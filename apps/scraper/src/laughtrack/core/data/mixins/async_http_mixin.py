"""
Async HTTP session management mixin for scrapers.

This mixin provides standardized aiohttp session management with proper
timeout configuration, header management, and cleanup.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional

import aiohttp

from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders


class AsyncHttpMixin(ABC):
    """
    Mixin that provides standardized async HTTP session management for scrapers.

    Features:
    - Automatic session creation and reuse
    - Proper timeout configuration from club settings
    - Header management integration
    - Automatic cleanup
    - Context manager support
    """

    @property
    @abstractmethod
    def club(self):
        """Club property that must be implemented by the using class."""
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session: Optional[aiohttp.ClientSession] = None
        self._default_headers: Optional[Dict[str, str]] = None

    async def get_session(self, headers: Optional[Dict[str, str]] = None) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session with proper configuration.

        Args:
            headers: Optional custom headers to merge with defaults

        Returns:
            Configured aiohttp ClientSession
        """
        if self._session is None or self._session.closed:
            # Get timeout from club if available, otherwise use default
            timeout_value = getattr(self.club, "timeout", 30) if hasattr(self.club, "timeout") else 30
            timeout = aiohttp.ClientTimeout(total=timeout_value)
            session_headers = self._build_session_headers(headers)

            self._session = aiohttp.ClientSession(timeout=timeout, headers=session_headers)

        return self._session

    def _build_session_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Build headers for the session.

        Args:
            custom_headers: Optional custom headers to merge

        Returns:
            Combined headers dictionary
        """
        # Start with default headers if not set
        if self._default_headers is None:
            self._default_headers = self._get_default_headers()

        headers = self._default_headers.copy()

        # Merge custom headers if provided
        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _get_default_headers(self) -> Dict[str, str]:
        """
        Get default headers for this scraper type.
        Override in subclasses for specific header requirements.

        Returns:
            Default headers dictionary
        """
        return BaseHeaders.get_headers()

    async def close_session(self):
        """Close the aiohttp session if it exists."""
        if self._session and not self._session.closed:
            await self._session.close()
            # Give the event loop time to clean up transports
            await asyncio.sleep(0.1)
            self._session = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close_session()

    # Cleanup hook for BaseScraper compatibility
    async def close(self):
        """Cleanup method called by BaseScraper."""
        await self.close_session()
