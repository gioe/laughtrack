"""
Standardized HTTP utilities for venue scrapers.

This module provides common HTTP patterns with consistent error handling,
logging, and URL normalization.

Playwright fallback
-------------------
When curl-cffi returns a non-200 status, an empty body, or a response
containing a known bot-block signature (Cloudflare "Just a moment", DataDome
challenge, "Access denied"), both ``fetch_html`` and ``fetch_json``
transparently retry the request with a ``PlaywrightBrowser`` instance.
``fetch_json`` additionally parses the browser-rendered body back into JSON —
Chromium wraps raw API responses in a ``<pre>`` block, so the fallback
extracts and decodes that content.  The fallback is:

* **Lazy** — the ``playwright`` package is only imported when the fallback is
  actually triggered.
* **Globally disable-able** — set ``PLAYWRIGHT_FALLBACK=0`` in the environment
  to skip the fallback entirely.
* **5xx-skipping** — a headless browser cannot rescue a server-side failure,
  so both methods return ``None`` on 5xx without attempting the retry.
"""

import html as _html_lib
import json as _json
import os
import re
from typing import Any, Dict, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.url import URLUtils

# ---------------------------------------------------------------------------
# Bot-block detection
# ---------------------------------------------------------------------------

# Case-insensitive substrings that indicate the page is a bot-challenge page
# rather than the actual content we wanted.
_BOT_BLOCK_SIGNATURES: tuple[str, ...] = (
    "just a moment",        # Cloudflare waiting room / challenge
    "_cf_chl_opt",          # Cloudflare challenge JS variable
    "<title>access denied</title>",  # Generic WAF block page (title-scoped to avoid false positives)
    "datadome",             # DataDome challenge interstitial
    "enable javascript and cookies to continue",  # Cloudflare human check
)


def _bot_block_reason(html: str) -> Optional[str]:
    """Return the matching bot-block signature found in *html*, or ``None``.

    The check is case-insensitive so it catches varying capitalisation.
    """
    lower = html.lower()
    for sig in _BOT_BLOCK_SIGNATURES:
        if sig in lower:
            return sig
    return None


# Chromium's default JSON-viewer wraps the raw response body in a <pre> block.
_PRE_BLOCK_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", flags=re.DOTALL | re.IGNORECASE)


def _parse_json_from_rendered_html(rendered: str) -> Optional[Any]:
    """Parse JSON out of a Playwright-rendered response body.

    When the fallback browser navigates to an API endpoint that returns
    ``application/json``, Chromium renders the page as
    ``<html><body><pre>…JSON…</pre></body></html>``.  Less commonly, the page
    body is the raw JSON text itself.  Try both strategies in order and return
    ``None`` if neither yields valid JSON.
    """
    stripped = rendered.strip()
    if stripped.startswith(("{", "[")):
        try:
            return _json.loads(stripped)
        except _json.JSONDecodeError:
            pass

    match = _PRE_BLOCK_RE.search(rendered)
    if match is not None:
        inner = _html_lib.unescape(match.group(1)).strip()
        try:
            return _json.loads(inner)
        except _json.JSONDecodeError:
            return None

    return None


# ---------------------------------------------------------------------------
# Lazy JS-fallback browser singleton
# ---------------------------------------------------------------------------

_js_browser: Optional[Any] = None  # PlaywrightBrowser, or _BROWSER_UNAVAILABLE sentinel

# Sentinel used after a failed import so we don't re-attempt (and re-warn) on every call.
_BROWSER_UNAVAILABLE = object()


def _get_js_browser() -> Optional[Any]:
    """Return the shared PlaywrightBrowser instance, or ``None`` when disabled.

    The browser is created lazily so that scrapers that never trigger a
    bot-block pay zero Playwright import overhead.

    Returns ``None`` when:
    * ``PLAYWRIGHT_FALLBACK=0`` is set in the environment, or
    * playwright is not installed (ImportError is swallowed with a warning,
      and ``_BROWSER_UNAVAILABLE`` is stored so the warning fires only once).
    """
    global _js_browser

    if os.environ.get("PLAYWRIGHT_FALLBACK", "1") == "0":
        return None

    if _js_browser is _BROWSER_UNAVAILABLE:
        return None

    if _js_browser is None:
        try:
            # Import here to keep playwright out of the top-level import graph
            from laughtrack.foundation.infrastructure.http.playwright_browser import (  # noqa: PLC0415
                PlaywrightBrowser,
            )

            _js_browser = PlaywrightBrowser()
        except ImportError:
            Logger.warn(
                "[HttpClient] playwright package not installed — JS fallback unavailable. "
                "Install it with: pip install playwright && playwright install chromium",
                {},
            )
            _js_browser = _BROWSER_UNAVAILABLE
            return None

    return _js_browser


async def close_js_browser() -> None:
    """Close and clear the shared PlaywrightBrowser singleton.

    Call this while the event loop is still running (e.g., at the end of
    _scrape_clubs_concurrently) so Playwright objects are closed on the same
    loop that created them — making the atexit handler a safe no-op.
    """
    global _js_browser
    browser = _js_browser
    if browser is None or browser is _BROWSER_UNAVAILABLE:
        return
    _js_browser = None
    await browser.close()


# ---------------------------------------------------------------------------
# HttpClient
# ---------------------------------------------------------------------------


class HttpClient:
    """
    Standardized HTTP client with consistent error handling and logging.

    Provides common HTTP patterns used across venue scrapers.
    """

    @staticmethod
    async def fetch_html(
        session: AsyncSession,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
        proxy_url: Optional[str] = None,
        raise_on_failure: bool = False,
        **request_kwargs: Any,
    ) -> Optional[str]:
        """
        Fetch HTML content from a URL with standardized error handling.

        If curl-cffi returns ``None``, an empty body, or a known bot-block
        response, the request is automatically retried with a Playwright
        headless browser.  Set ``PLAYWRIGHT_FALLBACK=0`` to disable this
        behaviour globally.

        Args:
            session: curl_cffi AsyncSession to use for the request
            url: URL to fetch (will be normalized)
            headers: Optional headers to include
            logger_context: Context for logging
            proxy_url: Optional proxy URL (e.g. "http://host:8080"). When
                provided the request is routed through that proxy.  Also
                applied to the Playwright browser context on fallback.
            raise_on_failure: When True, raise ``RequestsError`` (via
                ``response.raise_for_status()``) when the curl-cffi response
                is non-2xx and the Playwright fallback did not recover usable
                content.  This preserves the shared retry layer's ability to
                classify transient 5xx into ``NetworkError`` for exponential
                backoff.  Also short-circuits the Playwright attempt for 5xx
                responses (server errors cannot be rescued by a browser).
            **request_kwargs: Additional keyword arguments forwarded to
                ``session.get`` (e.g. ``timeout``).  Reserved names
                ``headers`` and ``proxies`` are handled explicitly.

        Returns:
            HTML content as string, or None if both curl-cffi and the
            Playwright fallback fail to return usable content.

        Raises:
            RequestsError: Only when ``raise_on_failure=True`` and the
                response is non-2xx with no Playwright rescue.
            Exception: Any network or connection error is re-raised so callers
                can log and handle it (avoids duplicate log entries).
        """
        logger_context = logger_context or {}
        normalized_url = URLUtils.normalize_url(url)

        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        response = await session.get(normalized_url, headers=headers, proxies=proxies, **request_kwargs)

        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_response(response.status_code)

        # 5xx is a server-side failure; a headless browser cannot rescue it.
        # Skip the Playwright attempt (saves 1–3 s per retry) and let the
        # caller's retry layer handle it via raise_for_status.
        if 500 <= response.status_code < 600:
            Logger.warn(
                f"HTTP {response.status_code} when fetching {normalized_url}",
                logger_context,
            )
            if raise_on_failure:
                response.raise_for_status()
            return None

        if response.status_code != 200:
            Logger.warn(
                f"HTTP {response.status_code} when fetching {normalized_url}",
                logger_context,
            )
            html: Optional[str] = None
        else:
            html = response.text

        # ------------------------------------------------------------------
        # Automatic JS fallback
        # ------------------------------------------------------------------
        fallback_reason: Optional[str] = None

        if html is None:
            fallback_reason = f"HTTP {response.status_code if response else 'error'}"
        elif not html.strip():
            fallback_reason = "empty body"
        else:
            bot_signature = _bot_block_reason(html)
            if bot_signature is not None:
                if diagnostics is not None:
                    diagnostics.record_bot_block(bot_signature)
                fallback_reason = bot_signature

        if fallback_reason is not None:
            browser = _get_js_browser()
            if browser is not None:
                if diagnostics is not None:
                    diagnostics.record_playwright_fallback()
                Logger.info(
                    f"[HttpClient] Triggering Playwright fallback for {normalized_url} "
                    f"(reason: {fallback_reason!r})",
                    logger_context,
                )
                try:
                    html = await browser.fetch_html(normalized_url, proxy_url=proxy_url)
                except Exception as exc:
                    Logger.warn(
                        f"[HttpClient] Playwright fallback failed for {normalized_url}: {exc}",
                        logger_context,
                    )
                    html = None

        # Preserve the old mixin contract: non-2xx without rescue → raise so
        # the shared retry layer (ErrorHandler.execute_with_retry) can classify
        # the error and drive exponential backoff.
        if raise_on_failure and html is None and response.status_code != 200:
            response.raise_for_status()

        return html

    @staticmethod
    async def fetch_json(
        session: AsyncSession,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
        proxy_url: Optional[str] = None,
    ) -> Optional[JSONDict]:
        """
        Fetch JSON data from a URL with standardized error handling.

        If curl-cffi returns a non-200 status, an empty body, or a known
        bot-block response, the request is automatically retried with a
        Playwright headless browser.  The browser renders the JSON endpoint,
        and the wrapping ``<pre>`` block (or raw body) is parsed back into
        JSON.  Set ``PLAYWRIGHT_FALLBACK=0`` to disable this behaviour globally.

        5xx responses skip the fallback — a server-side failure cannot be
        rescued by a headless browser.

        Args:
            session: curl_cffi AsyncSession to use for the request
            url: URL to fetch (will be normalized)
            headers: Optional headers to include
            logger_context: Context for logging
            proxy_url: Optional proxy URL (e.g. "http://host:8080"). When
                provided the request is routed through that proxy.  Also
                applied to the Playwright browser context on fallback.

        Returns:
            JSON data as dictionary, or None if the response is not usable
            and the Playwright fallback does not recover parseable JSON.

        Raises:
            Exception: Any network or connection error is re-raised so callers
                can log and handle it (avoids duplicate log entries).
        """
        logger_context = logger_context or {}

        # Normalize URL to ensure proper scheme
        normalized_url = URLUtils.normalize_url(url)

        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        response = await session.get(normalized_url, headers=headers, proxies=proxies)

        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_response(response.status_code)

        # 5xx is a server-side failure; a headless browser cannot rescue it.
        # Skip the Playwright attempt (saves 1–3 s per retry) — the caller's
        # retry layer classifies 5xx via the non-None return contract.
        if 500 <= response.status_code < 600:
            Logger.warn(
                f"HTTP {response.status_code} when fetching {normalized_url}",
                logger_context,
            )
            return None

        # ------------------------------------------------------------------
        # Decide whether the response is usable or needs the JS fallback
        # ------------------------------------------------------------------
        fallback_reason: Optional[str] = None

        if response.status_code != 200:
            Logger.warn(
                f"HTTP {response.status_code} when fetching {normalized_url}",
                logger_context,
            )
            fallback_reason = f"HTTP {response.status_code}"
            # A 4xx body served as HTML often contains a WAF challenge
            # (DataDome, Cloudflare). Detect the signature for log observability
            # even when diagnostics is absent, and prefer it as the fallback
            # reason so the Playwright activation log is informative.
            if response.text:
                bot_signature = _bot_block_reason(response.text)
                if bot_signature is not None:
                    if diagnostics is not None:
                        diagnostics.record_bot_block(bot_signature)
                    fallback_reason = bot_signature
        elif not response.text or not response.text.strip():
            Logger.warn(
                f"HTTP 200 with empty body when fetching {normalized_url}",
                logger_context,
            )
            fallback_reason = "empty body"
        else:
            # 200 with an HTML challenge (some WAFs return 200 + interstitial).
            bot_signature = _bot_block_reason(response.text)
            if bot_signature is not None:
                if diagnostics is not None:
                    diagnostics.record_bot_block(bot_signature)
                fallback_reason = bot_signature

        # ------------------------------------------------------------------
        # Automatic JS fallback
        # ------------------------------------------------------------------
        if fallback_reason is not None:
            browser = _get_js_browser()
            if browser is None:
                return None
            if diagnostics is not None:
                diagnostics.record_playwright_fallback()
            Logger.info(
                f"[HttpClient] Triggering Playwright fallback for {normalized_url} "
                f"(reason: {fallback_reason!r})",
                logger_context,
            )
            try:
                rendered = await browser.fetch_html(normalized_url, proxy_url=proxy_url)
            except Exception as exc:
                Logger.warn(
                    f"[HttpClient] Playwright fallback failed for {normalized_url}: {exc}",
                    logger_context,
                )
                return None
            parsed = _parse_json_from_rendered_html(rendered)
            if parsed is None:
                Logger.warn(
                    f"[HttpClient] Playwright fallback could not parse JSON from {normalized_url}",
                    logger_context,
                )
            return parsed

        return response.json()
