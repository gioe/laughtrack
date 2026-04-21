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
* **Per-call empty-body opt-out** — pass ``allow_empty_body=True`` to
  ``fetch_html`` or ``fetch_json`` when an HTTP-200 empty body is a
  legitimate signal rather than a failure (e.g. Tessera's stale-event
  response on Broadway Comedy Club, where the browser replay returns
  empty too and every stale event pays ~1–3 s of Chromium overhead for
  nothing). The WARN log and the fallback are both suppressed; the
  method returns ``None`` directly.

When the Playwright-rendered response *itself* matches a known bot-block
signature (WAF still blocking the headless browser), the signature is
recorded on the bound ``ScrapeDiagnostics`` with a ``playwright_`` prefix so
persistent WAF failures are distinguishable from curl-cffi-level blocks in
the triage report.
"""

import html as _html_lib
import json as _json
import os
import re
from typing import Any, Dict, Optional, Tuple

from curl_cffi.requests import AsyncSession, Response

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

    When the singleton was first launched on a worker-thread event loop,
    the main loop's ``close()`` call may hit a loop mismatch.  ``close()``
    now short-circuits in that case, but any residual RuntimeError (e.g.
    from a sibling Playwright future attached to a closed loop) is caught
    here so nightly teardown cannot propagate a cross-loop error up
    through ``scrape_shows`` and trigger the 90-minute GHA timeout.
    """
    global _js_browser
    browser = _js_browser
    if browser is None or browser is _BROWSER_UNAVAILABLE:
        return
    _js_browser = None
    try:
        await browser.close()
    except RuntimeError as exc:
        # Only the cross-loop signature is expected here; re-raise any other
        # RuntimeError so genuine transport failures remain visible.
        if "bound to a different event loop" not in str(exc):
            raise
        Logger.warn(f"[HttpClient] close_js_browser swallowed cross-loop RuntimeError: {exc}")


# ---------------------------------------------------------------------------
# HttpClient
# ---------------------------------------------------------------------------


class HttpClient:
    """
    Standardized HTTP client with consistent error handling and logging.

    Provides common HTTP patterns used across venue scrapers.
    """

    @staticmethod
    async def _fetch_with_fallback(
        session: AsyncSession,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
        proxy_url: Optional[str] = None,
        raise_on_failure: bool = False,
        allow_empty_body: bool = False,
        **request_kwargs: Any,
    ) -> Tuple[Optional[str], Response, bool]:
        """
        Shared fetch orchestration for ``fetch_html`` and ``fetch_json``.

        Issues a curl-cffi GET, evaluates the response for non-200/empty/bot-
        block conditions, and retries with the lazy Playwright singleton when
        appropriate.  The caller post-processes the returned body into the
        format it wants (raw HTML vs. parsed JSON).

        Args:
            allow_empty_body: When True, an HTTP-200 response with an
                empty or whitespace-only body is treated as a legitimate
                "no data" signal rather than a possible bot-block:
                returns ``(None, response, False)`` immediately with no
                WARN log and no Playwright fallback attempt.  Tessera
                uses this for its stale-event signature — the browser
                replay returns empty too, so the fallback is pure
                overhead (~1–3 s of Chromium launch per stale event).
                Non-200 and 200+bot-signature branches still trigger
                the fallback regardless of this flag.

        Returns:
            (html, response, fallback_invoked) where:
            * ``html`` — final HTML string, or ``None`` if neither curl-cffi
              nor the Playwright fallback produced usable content
            * ``response`` — the original curl-cffi response object (always
              set; never ``None`` on return)
            * ``fallback_invoked`` — ``True`` when the Playwright fallback
              was actually invoked (regardless of whether it succeeded).
              ``False`` when the curl-cffi body was used directly, or when
              a fallback reason was detected but ``_get_js_browser()``
              returned ``None`` (env-disabled or Playwright unavailable).
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
            return None, response, False

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
            # (DataDome, Cloudflare). Prefer the signature as the fallback
            # reason so the Playwright activation log is informative.
            if response.text:
                    bot_signature = _bot_block_reason(response.text)
                    if bot_signature is not None:
                        if diagnostics is not None:
                            diagnostics.record_bot_block(
                                bot_signature,
                                source="response_body",
                                stage="direct_fetch",
                            )
                    fallback_reason = bot_signature
        elif not response.text or not response.text.strip():
            # Caller has opted into empty-body-is-OK semantics (Tessera's
            # stale-event signal): short-circuit before the WARN and the
            # Playwright launch.  The browser replay returns empty too,
            # so the fallback would only burn Chromium startup time.
            if allow_empty_body:
                return None, response, False
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
                    diagnostics.record_bot_block(
                        bot_signature,
                        source="response_body",
                        stage="direct_fetch",
                    )
                fallback_reason = bot_signature

        if fallback_reason is None:
            return response.text, response, False

        # ------------------------------------------------------------------
        # Automatic JS fallback
        # ------------------------------------------------------------------
        browser = _get_js_browser()
        html: Optional[str] = None
        fallback_invoked = False
        if browser is not None:
            fallback_invoked = True
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

        # Playwright can return its own bot-challenge page when the WAF also
        # blocks the headless browser. Without this check the caller would
        # receive challenge HTML (fetch_html) or a failed JSON parse
        # (fetch_json) indistinguishably from "API returned unexpected HTML",
        # and the nightly triage report would only show the curl-cffi
        # signature. Record a prefixed signature so persistent WAF failures
        # are visible in the same report as curl-cffi-level blocks.
        if html is not None:
            rendered_bot_signature = _bot_block_reason(html)
            if rendered_bot_signature is not None:
                Logger.warn(
                    f"[HttpClient] Playwright fallback for {normalized_url} "
                    f"also returned a bot-block page "
                    f"(signature: {rendered_bot_signature!r})",
                    logger_context,
                )
                if diagnostics is not None:
                    diagnostics.record_bot_block(
                        f"playwright_{rendered_bot_signature}",
                        source="playwright_rendered_html",
                        stage="playwright_fallback",
                    )

        # Preserve the mixin contract: non-2xx without rescue → raise so the
        # shared retry layer (ErrorHandler.execute_with_retry) can classify
        # the error and drive exponential backoff.
        if raise_on_failure and html is None and response.status_code != 200:
            response.raise_for_status()

        return html, response, fallback_invoked

    @staticmethod
    async def fetch_html(
        session: AsyncSession,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
        proxy_url: Optional[str] = None,
        raise_on_failure: bool = False,
        allow_empty_body: bool = False,
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
            allow_empty_body: When True, an HTTP-200 empty body returns
                ``None`` immediately without warning or triggering the
                Playwright fallback.  Use this when the caller knows an
                empty body is a valid application-level signal.
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
        html, _response, _fallback_invoked = await HttpClient._fetch_with_fallback(
            session,
            url,
            headers=headers,
            logger_context=logger_context,
            proxy_url=proxy_url,
            raise_on_failure=raise_on_failure,
            allow_empty_body=allow_empty_body,
            **request_kwargs,
        )
        return html

    @staticmethod
    async def fetch_json(
        session: AsyncSession,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
        proxy_url: Optional[str] = None,
        allow_empty_body: bool = False,
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
            allow_empty_body: When True, an HTTP-200 empty body returns
                ``None`` immediately without warning or triggering the
                Playwright fallback.  Use this for endpoints where an
                empty body is the expected "no data" signal (e.g. a
                Tessera stale-event response on Broadway Comedy Club).

        Returns:
            JSON data as dictionary, or None if the response is not usable
            and the Playwright fallback does not recover parseable JSON.

        Raises:
            Exception: Any network or connection error is re-raised so callers
                can log and handle it (avoids duplicate log entries).
        """
        html, response, fallback_invoked = await HttpClient._fetch_with_fallback(
            session,
            url,
            headers=headers,
            logger_context=logger_context,
            proxy_url=proxy_url,
            allow_empty_body=allow_empty_body,
        )

        if html is None:
            return None

        if not fallback_invoked:
            return response.json()

        parsed = _parse_json_from_rendered_html(html)
        if parsed is None:
            Logger.warn(
                f"[HttpClient] Playwright fallback could not parse JSON from "
                f"{URLUtils.normalize_url(url)}",
                logger_context or {},
            )
        return parsed
