"""
HTTP convenience methods mixin for scrapers.

This module provides common HTTP operations with error handling and retry logic.

Playwright fallback parity
--------------------------
``fetch_html`` routes through ``HttpClient.fetch_html`` so every scraper
inherits the automatic Playwright rescue on 403 / empty-body / bot-block
responses.  ``fetch_json`` duplicates the same fallback inline (until
``HttpClient.fetch_json`` gains native support in TASK-1650 / A2): the URL is
re-fetched via the shared ``PlaywrightBrowser`` and the rendered body is
parsed as JSON, tolerating Chromium's ``<pre>``-wrapped JSON viewer output.
Set ``PLAYWRIGHT_FALLBACK=0`` to disable both paths globally.
"""

import json as _json
import re
from html import unescape as _html_unescape
from typing import Any, List, Optional, Protocol

from curl_cffi.requests import AsyncSession

from laughtrack.core.data.mixins.async_http_mixin import AsyncHttpMixin
from laughtrack.foundation.infrastructure.http.client import (
    HttpClient,
    _bot_block_reason,
    _get_js_browser,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.url import URLUtils


class HasErrorHandler(Protocol):
    """Protocol for classes that have an error handler."""

    error_handler: Any


_PRE_PATTERN = re.compile(r"<pre[^>]*>(.*?)</pre>", re.DOTALL | re.IGNORECASE)


def _parse_json_from_rendered(html: Optional[str]) -> Any:
    """Best-effort parse of JSON content from a Playwright-rendered page.

    Chromium wraps raw JSON bodies in its built-in JSON viewer
    (``<html>…<body><pre>JSON_HERE</pre>…``).  Extract the ``<pre>`` content
    when present; otherwise try parsing the document directly.
    """
    if not html:
        return None
    candidate = html.strip()
    match = _PRE_PATTERN.search(html)
    if match:
        candidate = _html_unescape(match.group(1)).strip()
    if not candidate:
        return None
    try:
        return _json.loads(candidate)
    except (ValueError, TypeError):
        return None


class HttpConvenienceMixin(AsyncHttpMixin):
    """
    Mixin providing convenient HTTP methods with error handling.

    Requires the including class to have an 'error_handler' attribute
    with an execute_with_retry method.
    """

    async def fetch_json(self, url: str, **kwargs) -> Any:
        """Fetch and parse JSON from URL with error handling and Playwright fallback.

        Raise-on-failure semantics match the pre-TASK-1649 behavior: a non-2xx
        response raises ``RequestsError`` (via ``response.raise_for_status()``)
        so the shared retry layer can classify 5xx into ``NetworkError`` for
        exponential backoff.  Playwright is NOT attempted for 5xx (server
        errors cannot be rescued by a browser).  For 4xx, bot-block, and
        empty-body cases the fallback fires; if it recovers, the raise is
        skipped.

        Returns:
            Parsed JSON data, or None if the response was 200 OK with an
            empty/whitespace-only body or bot-block signature and the
            Playwright fallback either is disabled or fails to recover a
            parseable body.
        """
        logger_context = getattr(self, "logger_context", None) or {}
        normalized_url = URLUtils.normalize_url(url)
        proxy_url = kwargs.pop("proxy_url", None)
        request_kwargs = dict(kwargs)
        if proxy_url is not None:
            request_kwargs["proxies"] = {"http": proxy_url, "https": proxy_url}

        async def _fetch_json():
            session = await self.get_session()
            response = await session.get(normalized_url, **request_kwargs)

            # 5xx: server error — Playwright can't rescue. Raise so the
            # retry layer can classify into NetworkError for backoff.
            if 500 <= response.status_code < 600:
                Logger.warn(
                    f"HTTP {response.status_code} when fetching {normalized_url}",
                    logger_context,
                )
                response.raise_for_status()

            fallback_reason: Optional[str] = None
            if response.status_code != 200:
                Logger.warn(
                    f"HTTP {response.status_code} when fetching {normalized_url}",
                    logger_context,
                )
                fallback_reason = f"HTTP {response.status_code}"
            else:
                body_text = response.text
                if not body_text or not body_text.strip():
                    Logger.warn(
                        f"HTTP 200 with empty body when fetching {normalized_url}",
                        logger_context,
                    )
                    fallback_reason = "empty body"
                else:
                    fallback_reason = _bot_block_reason(body_text)

            if fallback_reason is None:
                return response.json()

            browser = _get_js_browser()
            rescued: Any = None
            if browser is not None:
                Logger.info(
                    f"[HttpConvenienceMixin.fetch_json] Triggering Playwright fallback for "
                    f"{normalized_url} (reason: {fallback_reason!r})",
                    logger_context,
                )
                try:
                    rendered = await browser.fetch_html(normalized_url, proxy_url=proxy_url)
                    rescued = _parse_json_from_rendered(rendered)
                except Exception as exc:
                    Logger.warn(
                        f"[HttpConvenienceMixin.fetch_json] Playwright fallback failed for "
                        f"{normalized_url}: {exc}",
                        logger_context,
                    )

            # Non-2xx with no Playwright rescue → raise to preserve the old
            # retry contract (ErrorHandler.execute_with_retry classifies 4xx
            # as terminal and 5xx would already have raised above).
            if rescued is None and response.status_code != 200:
                response.raise_for_status()
            return rescued

        # Use error handler if available, otherwise execute directly
        error_handler = getattr(self, "error_handler", None)
        if error_handler and hasattr(error_handler, "execute_with_retry"):
            return await error_handler.execute_with_retry(_fetch_json, f"fetch_json_{url}")
        else:
            return await _fetch_json()

    async def fetch_json_list(self, url: str, **kwargs) -> Optional[List[Any]]:
        """Fetch and parse a root-level JSON array from URL with error handling.

        Use this instead of fetch_json() when the API is known to return a JSON
        array at the root level (e.g. Squarespace GetItemsByMonth, Ninkashi).

        Network failures raise exceptions (propagated from fetch_json). Returns
        None only when the parsed response is not a JSON array.
        """
        data = await self.fetch_json(url, **kwargs)
        if not isinstance(data, list):
            Logger.warn(f"fetch_json_list: expected list from {url}, got {type(data).__name__}")
            return None
        return data

    async def fetch_html(self, url: str, **kwargs) -> Optional[str]:
        """Fetch HTML content from URL with error handling and Playwright fallback.

        Delegates to ``HttpClient.fetch_html`` with ``raise_on_failure=True``
        so non-2xx responses (when the Playwright fallback cannot rescue them)
        raise ``RequestsError`` for the shared retry layer — preserving the
        pre-TASK-1649 contract that downstream scrapers depend on for 5xx
        exponential backoff and ``except NetworkError`` retry loops.
        """
        logger_context = getattr(self, "logger_context", None)

        async def _fetch_html():
            session = await self.get_session()
            return await HttpClient.fetch_html(
                session,
                url,
                logger_context=logger_context,
                raise_on_failure=True,
                **kwargs,
            )

        # Use error handler if available, otherwise execute directly
        error_handler = getattr(self, "error_handler", None)
        if error_handler and hasattr(error_handler, "execute_with_retry"):
            return await error_handler.execute_with_retry(_fetch_html, f"Fetch HTML: {url}")
        else:
            return await _fetch_html()

    async def fetch_html_bare(self, url: str) -> str:
        """Fetch HTML using a transient AsyncSession with impersonation only — no application headers.

        Use this instead of fetch_html() when the target site uses DataDome or similar
        bot detection that triggers on application header combinations. curl_cffi's
        impersonation fingerprint alone is sufficient and does not trigger DataDome.
        """

        timeout = getattr(getattr(self, "club", None), "timeout", 30) or 30

        async def _fetch_html_bare():
            async with AsyncSession(impersonate=self._get_impersonation_target(), timeout=timeout) as session:
                response = await session.get(url)
                response.raise_for_status()
                return response.text

        error_handler = getattr(self, "error_handler", None)
        if error_handler and hasattr(error_handler, "execute_with_retry"):
            return await error_handler.execute_with_retry(_fetch_html_bare, f"Fetch HTML bare: {url}")
        else:
            return await _fetch_html_bare()

    async def post_json(self, url: str, data: JSONDict, **kwargs) -> Optional[JSONDict]:
        """Post JSON data and get JSON response with error handling.

        Returns:
            Parsed JSON data, or None if the response body is empty or
            whitespace-only (HTTP 200 with no content).
        """
        session = await self.get_session()

        async def _post_json():
            response = await session.post(url, json=data, **kwargs)
            response.raise_for_status()
            if not response.text or not response.text.strip():
                Logger.warn(f"HTTP 200 with empty body when posting to {url}")
                return None
            return response.json()

        # Use error handler if available, otherwise execute directly
        error_handler = getattr(self, "error_handler", None)
        if error_handler and hasattr(error_handler, "execute_with_retry"):
            return await error_handler.execute_with_retry(_post_json, f"post_json_{url}")
        else:
            return await _post_json()

    async def post_form(self, url: str, data: str, **kwargs) -> str:
        """Post form data and get text response with error handling."""
        session = await self.get_session()

        async def _post_form():
            # Set default content type for form data if not provided
            headers = kwargs.get("headers", {})
            if "content-type" not in {k.lower() for k in headers.keys()}:
                headers = headers.copy()
                headers["content-type"] = "application/x-www-form-urlencoded"
                kwargs["headers"] = headers

            response = await session.post(url, data=data, **kwargs)
            response.raise_for_status()
            return response.text

        # Use error handler if available, otherwise execute directly
        error_handler = getattr(self, "error_handler", None)
        if error_handler and hasattr(error_handler, "execute_with_retry"):
            return await error_handler.execute_with_retry(_post_form, f"post_form_{url}")
        else:
            return await _post_form()
