"""Capsolver-backed Cloudflare "Just a moment" / Turnstile challenge solver.

The scraper already ships capsolver solvers for AWS WAF
(:mod:`aws_waf_solver`) and DataDome (:mod:`datadome_solver`), but had no
recovery path for Cloudflare's managed "Just a moment" interstitial /
Turnstile challenge. When a GHA datacenter IP hits a Cloudflare-protected
target and the passive wait (:meth:`PlaywrightBrowser._wait_for_cloudflare_challenge`,
TASK-2846) can't clear it — because the challenge is the *hard* interactive
Turnstile rather than the auto-clearing managed variant — the venue scrapes
0 shows with no recovery (West River Comedy Club / tickettailor, Stevie
Ray's / tickets.chanhassendt.com).

This module wraps capsolver.com's ``AntiCloudflareTask`` flow, which solves
the full interstitial through a proxy and returns a ``cf_clearance`` cookie
the caller injects back into the browser context before re-navigating —
exactly the cookie-injection shape AWS WAF and DataDome already use. For a
standalone Turnstile *widget* (no interstitial) it falls back to the
proxyless ``AntiTurnstileTaskProxyless`` flow, which returns only a token.

The shape mirrors :mod:`aws_waf_solver` and :mod:`datadome_solver`
deliberately — same ``CAPSOLVER_API_KEY`` guardrail, same
:func:`parse_set_cookie` helper, same optional proxy threading, same
createTask/getTaskResult poll loop.

Proxy note: Cloudflare binds ``cf_clearance`` to the IP that solved the
challenge, so ``AntiCloudflareTask`` requires a proxy and the caller must
issue the follow-up request through the *same* proxy. Without a proxy the
cookie flow is skipped (a clearance bound to capsolver's egress IP would be
rejected by the origin); only the proxyless token flow is attempted, and
only when the page exposes a Turnstile sitekey.

Guardrail: when ``CAPSOLVER_API_KEY`` is unset, ``build_default_cloudflare_solver()``
returns ``None`` and callers must skip the solver path entirely.
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

# Substrings present in a Cloudflare "Just a moment" managed-challenge page.
# Unlike AWS WAF (window globals), the Cloudflare signal lives in the rendered
# markup, so detection is a case-insensitive substring match. Centralized here
# so PlaywrightBrowser's challenge detection and this solver share one source
# of truth (mirrors :data:`aws_waf_solver.AWS_WAF_MARKERS`).
CLOUDFLARE_CHALLENGE_MARKERS: tuple[str, ...] = (
    "just a moment",
    "_cf_chl_opt",
    "enable javascript and cookies to continue",
)

# Stricter subset used to gate the *paid* interactive solve. ``just a moment``
# is deliberately excluded here: it is a page <title> that can legitimately
# appear in real content, and gating a capsolver call on it would burn paid
# solves on false positives. ``_cf_chl_opt`` (the challenge JS config object)
# and the JS-and-cookies notice are emitted only by a genuine Cloudflare
# challenge, so requiring one of them before solving keeps the broad markers
# for the cheap passive wait while bounding capsolver spend to real challenges.
CLOUDFLARE_INTERACTIVE_MARKERS: tuple[str, ...] = (
    "_cf_chl_opt",
    "enable javascript and cookies to continue",
)

# Cookie Cloudflare issues once a challenge clears. capsolver's
# ``AntiCloudflareTask`` returns it under ``solution.cookies.cf_clearance``;
# some response shapes also surface a full ``Set-Cookie`` under
# ``solution.cookie``. The solver normalizes a bare value into the Set-Cookie
# shape :func:`parse_set_cookie` expects, using this name. cf_clearance is set
# ``Secure; HttpOnly; SameSite=None`` by Cloudflare, so the normalized form
# matches what the origin would have set.
CF_CLEARANCE_COOKIE_NAME = "cf_clearance"

_CAPSOLVER_BASE_URL = "https://api.capsolver.com"
_DEFAULT_POLL_INTERVAL_SEC = 3.0
# Interactive Turnstile solves routinely take 30-90s, matching the AWS WAF
# ceiling rather than DataDome's faster slider.
_DEFAULT_TIMEOUT_SEC = 180.0
_HTTP_TIMEOUT_SEC = 30.0


class SolvedCloudflareClearance(NamedTuple):
    """Result of a successful Cloudflare solve.

    ``cookie`` is the raw ``cf_clearance`` ``Set-Cookie`` value (present for
    the ``AntiCloudflareTask`` interstitial flow); callers feed it through
    :func:`parse_set_cookie` before ``context.add_cookies``. ``token`` is the
    Turnstile response token (present for the proxyless widget flow); it has
    no cookie-injection path today and is surfaced for completeness/logging.
    Exactly one of the two is typically populated.
    """

    cookie: Optional[str]
    token: Optional[str]
    user_agent: str


class CloudflareSolverError(Exception):
    """Raised when capsolver returns a structured error (auth/quota/etc.)."""


def is_cloudflare_interactive_challenge(html: str) -> bool:
    """Heuristic: does *html* still carry Cloudflare challenge markers?

    Returns ``True`` when at least one marker from
    :data:`CLOUDFLARE_INTERACTIVE_MARKERS` appears in the rendered HTML
    (case-insensitive). Used by PlaywrightBrowser AFTER
    :meth:`_wait_for_cloudflare_challenge` has run — if the markers are still
    present the managed/passive wait failed and an interactive solve is
    required. Gates on the stricter marker set (not the broad
    ``CLOUDFLARE_CHALLENGE_MARKERS`` used for the passive wait) so a real page
    that merely contains the ``just a moment`` phrase does not trigger a paid
    capsolver call.
    """
    if not html:
        return False
    lowered = html.lower()
    return any(marker in lowered for marker in CLOUDFLARE_INTERACTIVE_MARKERS)


class CloudflareSolver:
    """Async client for the capsolver.com Cloudflare challenge flows."""

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
        website_key: Optional[str] = None,
        action: Optional[str] = None,
        cdata: Optional[str] = None,
    ) -> Optional[SolvedCloudflareClearance]:
        """Submit a Cloudflare challenge and poll until ready.

        With *proxy_url*: uses ``AntiCloudflareTask`` to solve the full "Just
        a moment" interstitial through that proxy, returning a ``cf_clearance``
        cookie bound to the proxy IP. The caller MUST issue the follow-up
        request through the same proxy.

        Without *proxy_url*: ``cf_clearance`` cannot be solved usefully (it
        would bind to capsolver's egress IP and be rejected), so the solver
        falls back to the proxyless ``AntiTurnstileTaskProxyless`` flow, which
        requires *website_key* and returns only a Turnstile token. When no
        *website_key* is available it logs and returns ``None``.

        Returns ``None`` when capsolver fails to produce a solution within
        ``timeout_sec`` or the response is missing the expected field. Raises
        :class:`CloudflareSolverError` on capsolver-reported errors (auth,
        quota, bad payload) so the caller can distinguish a configuration
        problem from a slow solve.
        """
        metadata: dict[str, Any] = {}
        if action is not None:
            metadata["action"] = action
        if cdata is not None:
            metadata["cdata"] = cdata

        if proxy_url:
            # AntiCloudflareTask solves the interstitial and returns
            # cf_clearance bound to the supplied proxy IP. websiteKey is
            # optional for the managed challenge (Cloudflare embeds it in the
            # challenge page); pass it through when the DOM exposed one.
            task_payload: dict[str, Any] = {
                "type": "AntiCloudflareTask",
                "websiteURL": website_url,
                "userAgent": user_agent,
                "proxy": proxy_url,
            }
            if website_key is not None:
                task_payload["websiteKey"] = website_key
            if metadata:
                task_payload["metadata"] = metadata
        else:
            # No proxy: only the proxyless Turnstile-token flow is viable, and
            # it hard-requires the site key.
            if not website_key:
                Logger.warn(
                    "[CloudflareSolver] No proxy and no Turnstile sitekey — "
                    "cannot solve the interstitial without a proxy "
                    "(cf_clearance is IP-bound) and cannot run the proxyless "
                    "token flow without a sitekey; skipping solve",
                    {"website_url": website_url},
                )
                return None
            task_payload = {
                "type": "AntiTurnstileTaskProxyless",
                "websiteURL": website_url,
                "websiteKey": website_key,
            }
            if metadata:
                task_payload["metadata"] = metadata

        create_data = await self._post_json(
            f"{_CAPSOLVER_BASE_URL}/createTask",
            {"clientKey": self._api_key, "task": task_payload},
        )
        if not isinstance(create_data, dict):
            return None
        if create_data.get("errorId"):
            raise CloudflareSolverError(
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
                    f"[CloudflareSolver] Timed out polling capsolver after "
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
                raise CloudflareSolverError(
                    f"capsolver getTaskResult error: "
                    f"{data.get('errorCode')} — {data.get('errorDescription')}"
                )
            if data.get("status") == "ready":
                return self._parse_solution(data.get("solution") or {}, user_agent)
            # status == "processing" — keep polling

    @staticmethod
    def _parse_solution(
        solution: dict, fallback_user_agent: str
    ) -> Optional[SolvedCloudflareClearance]:
        """Extract a cf_clearance cookie and/or Turnstile token from *solution*.

        ``AntiCloudflareTask`` returns ``{"cookies": {"cf_clearance": "..."},
        "token": "...", "userAgent": "..."}`` (and some shapes surface a full
        Set-Cookie under ``cookie``); ``AntiTurnstileTaskProxyless`` returns
        ``{"token": "...", "userAgent": "..."}`` with no cookie.
        """
        token = solution.get("token")
        user_agent = solution.get("userAgent") or fallback_user_agent

        cookie: Optional[str] = None
        # Preferred shape: AntiCloudflareTask returns the clearance under
        # ``solution.cookies.cf_clearance`` (a bare value). Wrap it into a
        # Set-Cookie with the attributes Cloudflare itself uses; the caller's
        # default_domain supplies Domain via parse_set_cookie.
        cookies = solution.get("cookies")
        if isinstance(cookies, dict):
            cf_value = cookies.get(CF_CLEARANCE_COOKIE_NAME)
            if cf_value:
                cf_value = str(cf_value)
                cookie = (
                    cf_value
                    if cf_value.startswith(f"{CF_CLEARANCE_COOKIE_NAME}=")
                    else f"{CF_CLEARANCE_COOKIE_NAME}={cf_value}; "
                    "Path=/; Secure; HttpOnly; SameSite=None"
                )
        # Fallback: a full Set-Cookie under ``solution.cookie``. Only accept it
        # when it is explicitly a cf_clearance cookie — capsolver returns the
        # clearance under ``cookies`` for Cloudflare, so a ``cookie`` field
        # naming something else is not our clearance and must not be wrapped
        # (wrapping it would mangle an unrelated Set-Cookie into a bogus
        # cf_clearance value).
        if cookie is None:
            raw = solution.get("cookie")
            if raw and str(raw).startswith(f"{CF_CLEARANCE_COOKIE_NAME}="):
                cookie = str(raw)

        if not cookie and not token:
            return None
        return SolvedCloudflareClearance(
            cookie=cookie,
            token=token,
            user_agent=user_agent,
        )

    async def _post_json(self, url: str, payload: dict) -> Any:
        """POST JSON to *url* and return the parsed body.

        Isolated as a method so tests can override it without dragging in
        aiohttp. Uses ``certifi``'s CA bundle for TLS verification — mirrors
        :meth:`AwsWafSolver._post_json` / :meth:`DataDomeSolver._post_json`
        (macOS stdlib ssl ships no usable trust store, so a plain
        ``aiohttp.ClientSession()`` raises ``CERTIFICATE_VERIFY_FAILED``
        against ``api.capsolver.com``).
        """
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


def build_default_cloudflare_solver() -> Optional[CloudflareSolver]:
    """Build a solver from the ``CAPSOLVER_API_KEY`` env var, or ``None``.

    The ``None`` return value is the guardrail mirroring the AWS WAF / DataDome
    paths: callers must skip the solver entirely when the env var is unset,
    preserving existing behavior on non-Cloudflare sites and in unconfigured
    environments. capsolver issues every task type under one API key, so
    reusing :data:`CAPSOLVER_API_KEY_ENV` keeps the operator-facing surface to
    a single secret.
    """
    api_key = os.environ.get(CAPSOLVER_API_KEY_ENV)
    if not api_key:
        return None
    return CloudflareSolver(api_key)


__all__ = [
    "CF_CLEARANCE_COOKIE_NAME",
    "CLOUDFLARE_CHALLENGE_MARKERS",
    "CLOUDFLARE_INTERACTIVE_MARKERS",
    "CloudflareSolver",
    "CloudflareSolverError",
    "SolvedCloudflareClearance",
    "build_default_cloudflare_solver",
    "is_cloudflare_interactive_challenge",
    "parse_set_cookie",
]
