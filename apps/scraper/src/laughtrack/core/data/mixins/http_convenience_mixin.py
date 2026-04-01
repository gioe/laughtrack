"""
HTTP convenience methods mixin for scrapers.

This module provides common HTTP operations with error handling and retry logic.
"""

from typing import Any, Dict, List, Optional, Protocol

from curl_cffi.requests import AsyncSession

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.data.mixins.async_http_mixin import AsyncHttpMixin


class HasErrorHandler(Protocol):
    """Protocol for classes that have an error handler."""

    error_handler: Any


class HttpConvenienceMixin(AsyncHttpMixin):
    """
    Mixin providing convenient HTTP methods with error handling.

    Requires the including class to have an 'error_handler' attribute
    with an execute_with_retry method.
    """

    async def fetch_json(self, url: str, **kwargs) -> Any:
        """Fetch and parse JSON from URL with error handling.

        Returns:
            Parsed JSON data, or None if the response body is empty or
            whitespace-only (HTTP 200 with no content).
        """

        async def _fetch_json():
            session = await self.get_session()
            response = await session.get(url, **kwargs)
            response.raise_for_status()
            if not response.text or not response.text.strip():
                Logger.warn(f"HTTP 200 with empty body when fetching {url}")
                return None
            return response.json()

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

    async def fetch_html(self, url: str, **kwargs) -> str:
        """Fetch HTML content from URL with error handling."""

        async def _fetch_html():
            session = await self.get_session()
            response = await session.get(url, **kwargs)
            response.raise_for_status()
            return response.text

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

    async def post_json(self, url: str, data: JSONDict, **kwargs) -> JSONDict:
        """Post JSON data and get JSON response with error handling."""
        session = await self.get_session()

        async def _post_json():
            response = await session.post(url, json=data, **kwargs)
            response.raise_for_status()
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
