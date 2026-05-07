"""Capsolver-backed AWS WAF interactive-CAPTCHA solver.

When AWS WAF's passive JavaScript challenge can't sign a valid mp_verify
payload (typical when the request comes from headless Playwright through a
DataDome-cleared cookie), the WAF escalates to an interactive "Human
Verification" page. Etix layers AWS WAF *behind* DataDome — once
TASK-1658's DataDome cookie unlocks the origin, the next response is the
WAF interactive CAPTCHA. Without solving this second layer the 16 Etix
venues from the TASK-1647 audit still scrape 0 shows.

This module wraps capsolver.com's ``AntiAwsWafTaskProxyless`` flow and
returns the solved cookie (typically ``aws-waf-token=...``) that the
caller injects back into the browser context to retry the origin URL.
The shape mirrors :mod:`datadome_solver` deliberately — same env-var
guardrail, same Set-Cookie parsing helper, same optional proxy threading
— so future protection-system additions (Kasada, PerimeterX, etc.) have
a stable pattern to follow.

Guardrail: when ``CAPSOLVER_API_KEY`` is unset, ``build_default_aws_waf_solver()``
returns ``None`` and callers must skip the solver path entirely. This
preserves existing behavior on non-WAF sites and in unconfigured
environments — the caller's bot-block detector handles the rest.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, NamedTuple, Optional

from laughtrack.foundation.infrastructure.http.protection.datadome_solver import (
    CAPSOLVER_API_KEY_ENV,
    parse_set_cookie,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Markers AWS WAF's challenge script writes onto ``window``. Both the
# passive challenge AND the interactive "Human Verification" page emit
# them; the interactive page is detected by checking that they are STILL
# present after :meth:`PlaywrightBrowser._wait_for_waf_challenge` has run
# (i.e. the passive crypto failed to clear them). Centralized here so the
# solver and PlaywrightBrowser share a single source of truth.
AWS_WAF_MARKERS: tuple[str, ...] = (
    "awsWafCookieDomainList",
    "gokuProps",
)

# Cookie name AWS WAF expects for its issued token. capsolver's
# AntiAwsWafTask* response shape is inconsistent: some flows return a
# full ``aws-waf-token=<v>; Domain=...; Path=...`` Set-Cookie string,
# others return only the raw signed token value. The solver normalizes
# both into the Set-Cookie shape :func:`parse_set_cookie` expects, using
# this constant as the canonical name when the response was a bare
# token. Verified live against capsolver on 2026-05-07 — etix's
# AntiAwsWafTaskProxyless flow returns the bare-token form.
AWS_WAF_TOKEN_COOKIE_NAME = "aws-waf-token"

_CAPSOLVER_BASE_URL = "https://api.capsolver.com"
_DEFAULT_POLL_INTERVAL_SEC = 3.0
_DEFAULT_TIMEOUT_SEC = 180.0
_HTTP_TIMEOUT_SEC = 30.0


class SolvedAwsWafCookie(NamedTuple):
    """Result of a successful AWS WAF solve.

    ``cookie`` is the raw ``Set-Cookie`` value capsolver returns. For
    AWS WAF tokens this typically starts with ``aws-waf-token=``; the
    response sometimes omits a Domain attribute, so callers should pass
    the origin hostname through :func:`parse_set_cookie`'s ``default_domain``
    argument before handing the result to Playwright's ``add_cookies``.
    """

    cookie: str
    user_agent: str


class AwsWafSolverError(Exception):
    """Raised when capsolver returns a structured error (auth/quota/etc.)."""


def is_aws_waf_interactive_challenge(html: str) -> bool:
    """Heuristic: does *html* still carry AWS WAF challenge markers?

    Returns ``True`` when at least one marker from :data:`AWS_WAF_MARKERS`
    appears in the rendered HTML. Used by PlaywrightBrowser AFTER the
    passive-challenge wait has run — if the markers are still present
    the passive crypto failed and an interactive solve is required.
    """
    if not html:
        return False
    return any(marker in html for marker in AWS_WAF_MARKERS)


class AwsWafSolver:
    """Async client for the capsolver.com ``AntiAwsWafTaskProxyless`` flow."""

    def __init__(
        self,
        api_key: str,
        *,
        poll_interval_sec: float = _DEFAULT_POLL_INTERVAL_SEC,
        timeout_sec: float = _DEFAULT_TIMEOUT_SEC,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string")
        self._api_key = api_key
        self._poll_interval_sec = poll_interval_sec
        self._timeout_sec = timeout_sec

    async def solve(
        self,
        *,
        website_url: str,
        user_agent: str,
        proxy_url: Optional[str] = None,
        aws_key: Optional[str] = None,
        aws_iv: Optional[str] = None,
        aws_context: Optional[str] = None,
        aws_challenge_js: Optional[str] = None,
    ) -> Optional[SolvedAwsWafCookie]:
        """Submit an AWS WAF challenge and poll until ready.

        Returns ``None`` when capsolver fails to produce a solution within
        ``timeout_sec`` or when the response is missing the cookie field.
        Raises :class:`AwsWafSolverError` on capsolver-reported errors
        (auth, quota, bad payload, etc.) so the caller can distinguish a
        configuration problem from a slow solve.

        AWS WAF interactive challenges run a longer poll budget than
        DataDome (see :data:`_DEFAULT_TIMEOUT_SEC`) — the visible CAPTCHA
        used by AWS routinely takes 30–90 s to clear. The wider ceiling
        is the difference between a solved fetch and a false-positive
        timeout.

        ``aws_key``/``aws_iv``/``aws_context`` are the per-challenge
        crypto material AWS WAF embeds in ``window.gokuProps`` on the
        Human Verification page; ``aws_challenge_js`` is the challenge
        bootstrapper URL (typically
        ``https://<id>.token.awswaf.com/.../challenge.js``). Live
        verification on 2026-05-07 confirmed that capsolver returns a
        token bound to *that specific* challenge instance — omitting
        them yields a generic etix.com token that AWS WAF rejects on
        reload (issuing a fresh challenge with new key/iv/context).
        Callers without access to the challenge page can still call
        without these args, but the resulting token will not unlock the
        origin.
        """
        # AntiAwsWafTaskProxyless accepts websiteURL + userAgent as the
        # minimal payload, but for a token to actually unlock AWS WAF
        # the per-challenge key/iv/context must be passed through —
        # capsolver's worker computes a signature against THOSE values
        # and AWS WAF rejects any other.
        task_payload: dict[str, Any] = {
            "type": "AntiAwsWafTaskProxyless",
            "websiteURL": website_url,
            "userAgent": user_agent,
        }
        if aws_key is not None:
            task_payload["awsKey"] = aws_key
        if aws_iv is not None:
            task_payload["awsIv"] = aws_iv
        if aws_context is not None:
            task_payload["awsContext"] = aws_context
        if aws_challenge_js is not None:
            task_payload["awsChallengeJS"] = aws_challenge_js
        if proxy_url:
            # Switch to the proxied task type so capsolver routes the
            # solve through the caller's proxy. Required when WAF binds
            # the issued cookie to a residential IP.
            task_payload["type"] = "AntiAwsWafTask"
            task_payload["proxy"] = proxy_url

        create_data = await self._post_json(
            f"{_CAPSOLVER_BASE_URL}/createTask",
            {"clientKey": self._api_key, "task": task_payload},
        )
        if not isinstance(create_data, dict):
            return None
        if create_data.get("errorId"):
            raise AwsWafSolverError(
                f"capsolver createTask error: "
                f"{create_data.get('errorCode')} — {create_data.get('errorDescription')}"
            )
        task_id = create_data.get("taskId")
        if not task_id:
            return None

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout_sec
        while True:
            if loop.time() >= deadline:
                Logger.warn(
                    f"[AwsWafSolver] Timed out polling capsolver after "
                    f"{self._timeout_sec}s for task {task_id}",
                    {"task_id": task_id},
                )
                return None
            await asyncio.sleep(self._poll_interval_sec)
            data = await self._post_json(
                f"{_CAPSOLVER_BASE_URL}/getTaskResult",
                {"clientKey": self._api_key, "taskId": task_id},
            )
            if not isinstance(data, dict):
                return None
            if data.get("errorId"):
                raise AwsWafSolverError(
                    f"capsolver getTaskResult error: "
                    f"{data.get('errorCode')} — {data.get('errorDescription')}"
                )
            status = data.get("status")
            if status == "ready":
                solution = data.get("solution") or {}
                cookie = solution.get("cookie")
                if not cookie:
                    return None
                # Normalize bare-token responses to Set-Cookie shape so
                # the downstream parse_set_cookie call works uniformly.
                # The bare token is ``uuid:envelope:base64-signature``
                # — colons separate the parts, but the base64 signature
                # routinely contains ``=`` padding, which means a naive
                # ``"=" not in cookie`` check trips on those padding
                # bytes and skips the prefix. The reliable signal is the
                # canonical cookie name itself: a real Set-Cookie starts
                # with ``aws-waf-token=`` (capsolver, when it returns the
                # full form, always uses that name).
                #
                # Attributes matter: AWS WAF rejects the cookie unless
                # it matches what its own challenge.js would set.
                # Headed-mode capture on 2026-05-07 against
                # www.etix.com confirmed: ``Secure; SameSite=Lax`` (no
                # HttpOnly, no Domain — the caller's
                # ``default_domain`` argument provides it). Adding
                # these here keeps the integration site simple — it
                # just calls ``parse_set_cookie`` and trusts the
                # solver to have produced a syntactically complete
                # cookie.
                if not cookie.startswith(f"{AWS_WAF_TOKEN_COOKIE_NAME}="):
                    cookie = (
                        f"{AWS_WAF_TOKEN_COOKIE_NAME}={cookie}; "
                        "Path=/; Secure; SameSite=Lax"
                    )
                return SolvedAwsWafCookie(
                    cookie=cookie,
                    user_agent=solution.get("userAgent") or user_agent,
                )
            # status == "processing" — keep polling

    async def _post_json(self, url: str, payload: dict) -> Any:
        """POST JSON to *url* and return the parsed body.

        Isolated as a method so tests can override it without dragging in
        aiohttp. Production path uses aiohttp.ClientSession (already a
        declared core dependency in ``pyproject.toml``).

        Uses ``certifi``'s CA bundle for TLS verification — Python's
        stdlib ssl module on macOS does not ship with a usable trust
        store, so a plain ``aiohttp.ClientSession()`` raises
        ``CERTIFICATE_VERIFY_FAILED`` against ``api.capsolver.com``.
        Mirrors :class:`DataDomeSolver._post_json` for the same reason.
        """
        # Lazy imports — keep aiohttp/ssl/certifi off the cold path for
        # callers that never trigger an AWS WAF solve.
        import ssl  # noqa: PLC0415

        import aiohttp  # noqa: PLC0415
        import certifi  # noqa: PLC0415

        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        timeout = aiohttp.ClientTimeout(total=_HTTP_TIMEOUT_SEC)
        async with aiohttp.ClientSession(
            timeout=timeout, connector=connector
        ) as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json(content_type=None)


def build_default_aws_waf_solver() -> Optional[AwsWafSolver]:
    """Build a solver from the ``CAPSOLVER_API_KEY`` env var, or ``None``.

    The ``None`` return value is the guardrail mirroring TASK-1658's
    DataDome path: callers must skip the solver entirely when the env
    var is unset, preserving existing behavior on non-WAF sites and in
    unconfigured environments. capsolver issues both ``DatadomeSliderTask``
    and ``AntiAwsWafTask*`` under one API key, so reusing
    :data:`CAPSOLVER_API_KEY_ENV` keeps the operator-facing surface to a
    single secret.
    """
    api_key = os.environ.get(CAPSOLVER_API_KEY_ENV)
    if not api_key:
        return None
    return AwsWafSolver(api_key)


__all__ = [
    "AWS_WAF_MARKERS",
    "AWS_WAF_TOKEN_COOKIE_NAME",
    "AwsWafSolver",
    "AwsWafSolverError",
    "SolvedAwsWafCookie",
    "build_default_aws_waf_solver",
    "is_aws_waf_interactive_challenge",
    "parse_set_cookie",
]
