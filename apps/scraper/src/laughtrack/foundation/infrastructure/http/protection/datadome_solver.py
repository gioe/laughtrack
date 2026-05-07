"""Capsolver-backed DataDome interactive-CAPTCHA solver.

When DataDome serves an interactive visible-CAPTCHA challenge (mode ``bv``,
deployed platform-wide on etix.com on 2026-04-16 — see TASK-1647 audit),
neither curl-cffi impersonation nor Playwright stealth defeats it. The
challenge has to be solved out-of-band. This module wraps the capsolver.com
API (``createTask`` + ``getTaskResult`` polling) for the
``DatadomeSliderTask`` challenge type and returns the solved cookie that
the caller injects back into the browser context to retry the origin URL.

Guardrail: when ``CAPSOLVER_API_KEY`` is unset, ``build_default_solver()``
returns ``None`` and callers must skip the solver path entirely. This keeps
non-DataDome scrapers and unconfigured environments unchanged.

Sibling module: ``datadome_handler.py`` is the *detection* surface used by
the curl-cffi clients (Tixr today, more callers expected). This module is
the *solving* surface used by the Playwright fallback.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, NamedTuple, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger

CAPSOLVER_API_KEY_ENV = "CAPSOLVER_API_KEY"
DATADOME_IFRAME_HOST = "geo.captcha-delivery.com"

_CAPSOLVER_BASE_URL = "https://api.capsolver.com"
_DEFAULT_POLL_INTERVAL_SEC = 2.0
_DEFAULT_TIMEOUT_SEC = 90.0
_HTTP_TIMEOUT_SEC = 30.0


class SolvedCookie(NamedTuple):
    """Result of a successful DataDome solve.

    ``cookie`` is the raw ``Set-Cookie`` value capsolver returns (it
    typically looks like ``datadome=ABC...; Domain=.example.com; Path=/;
    Max-Age=...; Secure; SameSite=Lax``); callers feed it through
    :func:`parse_set_cookie` before passing it to Playwright's
    ``context.add_cookies``.
    """

    cookie: str
    user_agent: str


class DataDomeSolverError(Exception):
    """Raised when capsolver returns a structured error (auth/quota/etc.)."""


def is_datadome_iframe_url(src: Optional[str]) -> bool:
    """Heuristic: is *src* a DataDome interactive-CAPTCHA iframe URL?"""
    return bool(src) and DATADOME_IFRAME_HOST in src


def parse_set_cookie(
    set_cookie: str, default_domain: Optional[str] = None
) -> Optional[dict]:
    """Convert a ``Set-Cookie`` string to the dict Playwright wants.

    Returns ``None`` if the value can't be split into ``name=value`` or if
    no domain can be resolved (Playwright's ``add_cookies`` requires a
    domain). ``default_domain`` is used when the ``Set-Cookie`` itself
    omits a Domain attribute (rare, but capsolver has been observed to
    return bare cookies for some hosts).
    """
    if not set_cookie:
        return None
    parts = [p.strip() for p in set_cookie.split(";") if p.strip()]
    if not parts:
        return None
    name_value = parts[0]
    if "=" not in name_value:
        return None
    name, _, value = name_value.partition("=")
    cookie: dict = {"name": name.strip(), "value": value.strip()}
    domain = default_domain
    path = "/"
    secure = False
    http_only = False
    same_site: Optional[str] = None
    for attr in parts[1:]:
        key, _, val = attr.partition("=")
        k = key.strip().lower()
        v = val.strip()
        if k == "domain":
            domain = v or domain
        elif k == "path":
            path = v or path
        elif k == "secure":
            secure = True
        elif k == "httponly":
            http_only = True
        elif k == "samesite":
            vlow = v.lower()
            if vlow in ("strict", "lax", "none"):
                same_site = vlow.capitalize()
    if not domain:
        return None
    cookie["domain"] = domain
    cookie["path"] = path
    if secure:
        cookie["secure"] = True
    if http_only:
        cookie["httpOnly"] = True
    if same_site is not None:
        cookie["sameSite"] = same_site
    return cookie


class DataDomeSolver:
    """Async client for the capsolver.com ``DatadomeSliderTask`` flow."""

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
        captcha_url: str,
        website_url: str,
        user_agent: str,
        proxy_url: Optional[str] = None,
    ) -> Optional[SolvedCookie]:
        """Submit a DataDome challenge and poll until ready.

        Returns ``None`` when capsolver fails to produce a solution within
        ``timeout_sec`` or when the response is missing the cookie field.
        Raises :class:`DataDomeSolverError` on capsolver-reported errors
        (auth, quota, bad payload, etc.) so the caller can distinguish a
        configuration problem from a slow solve.
        """
        task_payload: dict[str, Any] = {
            "type": "DatadomeSliderTask",
            "websiteURL": website_url,
            "captchaUrl": captcha_url,
            "userAgent": user_agent,
        }
        if proxy_url:
            task_payload["proxy"] = proxy_url

        create_data = await self._post_json(
            f"{_CAPSOLVER_BASE_URL}/createTask",
            {"clientKey": self._api_key, "task": task_payload},
        )
        if not isinstance(create_data, dict):
            return None
        if create_data.get("errorId"):
            raise DataDomeSolverError(
                f"capsolver createTask error: "
                f"{create_data.get('errorCode')} — {create_data.get('errorDescription')}"
            )
        task_id = create_data.get("taskId")
        if not task_id:
            return None

        loop = asyncio.get_event_loop()
        deadline = loop.time() + self._timeout_sec
        while True:
            if loop.time() >= deadline:
                Logger.warn(
                    f"[DataDomeSolver] Timed out polling capsolver after "
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
                raise DataDomeSolverError(
                    f"capsolver getTaskResult error: "
                    f"{data.get('errorCode')} — {data.get('errorDescription')}"
                )
            status = data.get("status")
            if status == "ready":
                solution = data.get("solution") or {}
                cookie = solution.get("cookie")
                if not cookie:
                    return None
                return SolvedCookie(
                    cookie=cookie,
                    user_agent=solution.get("userAgent") or user_agent,
                )
            # status == "processing" — keep polling

    async def _post_json(self, url: str, payload: dict) -> Any:
        """POST JSON to *url* and return the parsed body.

        Isolated as a method so tests can override it without dragging in
        aiohttp. Production path uses aiohttp.ClientSession (already a
        declared core dependency in ``pyproject.toml``).
        """
        # Lazy import — keeps aiohttp out of the import graph for callers
        # that never trigger a DataDome solve.
        import aiohttp  # noqa: PLC0415

        timeout = aiohttp.ClientTimeout(total=_HTTP_TIMEOUT_SEC)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json(content_type=None)


def build_default_solver() -> Optional[DataDomeSolver]:
    """Build a solver from the ``CAPSOLVER_API_KEY`` env var, or ``None``.

    The ``None`` return value is the guardrail required by TASK-1658
    criterion 5518: callers must skip the solver path entirely when the
    env var is unset, preserving existing behavior on non-DataDome sites
    and in unconfigured environments.
    """
    api_key = os.environ.get(CAPSOLVER_API_KEY_ENV)
    if not api_key:
        return None
    return DataDomeSolver(api_key)
