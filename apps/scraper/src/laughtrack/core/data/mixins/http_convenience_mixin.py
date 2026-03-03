"""
HTTP convenience methods mixin for scrapers.

This module provides common HTTP operations with error handling and retry logic.
"""

from typing import Any, Dict, Protocol

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

    async def fetch_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """Fetch and parse JSON from URL with error handling."""

        async def _fetch_json():
            session = await self.get_session()
            async with session.get(url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()

        # Use error handler if available, otherwise execute directly
        error_handler = getattr(self, "error_handler", None)
        if error_handler and hasattr(error_handler, "execute_with_retry"):
            return await error_handler.execute_with_retry(_fetch_json, f"fetch_json_{url}")
        else:
            return await _fetch_json()

    async def fetch_html(self, url: str, **kwargs) -> str:
        """Fetch HTML content from URL with error handling."""

        async def _fetch_html():
            session = await self.get_session()
            async with session.get(url, **kwargs) as response:
                response.raise_for_status()
                return await response.text()

        # Use error handler if available, otherwise execute directly
        error_handler = getattr(self, "error_handler", None)
        if error_handler and hasattr(error_handler, "execute_with_retry"):
            return await error_handler.execute_with_retry(_fetch_html, f"Fetch HTML: {url}")
        else:
            return await _fetch_html()

    async def post_json(self, url: str, data: JSONDict, **kwargs) -> JSONDict:
        """Post JSON data and get JSON response with error handling."""
        session = await self.get_session()

        async def _post_json():
            async with session.post(url, json=data, **kwargs) as response:
                response.raise_for_status()
                return await response.json()

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

            async with session.post(url, data=data, **kwargs) as response:
                response.raise_for_status()
                return await response.text()

        # Use error handler if available, otherwise execute directly
        error_handler = getattr(self, "error_handler", None)
        if error_handler and hasattr(error_handler, "execute_with_retry"):
            return await error_handler.execute_with_retry(_post_form, f"post_form_{url}")
        else:
            return await _post_form()
