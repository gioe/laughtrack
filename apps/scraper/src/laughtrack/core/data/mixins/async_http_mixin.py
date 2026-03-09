"""
Async HTTP session management mixin for scrapers.

This mixin provides standardized aiohttp session management with proper
timeout configuration, header management, and cleanup.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional

from curl_cffi.requests import AsyncSession

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
        self._session: Optional[AsyncSession] = None
        self._session_closed: bool = True
        self._default_headers: Optional[Dict[str, str]] = None
        self._session_impersonation_target: Optional[str] = None
        self._session_proxy_url: Optional[str] = None

    async def get_session(
        self,
        headers: Optional[Dict[str, str]] = None,
        proxy_url: Optional[str] = None,
    ) -> AsyncSession:
        """
        Get or create curl_cffi AsyncSession with proper configuration.

        Args:
            headers: Optional custom headers to merge with defaults
            proxy_url: Optional proxy URL to route the session through
                (format: "http://proxy_url"). When provided, forwarded to
                AsyncSession as the ``proxy`` parameter.

        Returns:
            Configured curl_cffi AsyncSession impersonating Chrome
        """
        # Invalidate the session if the active BrowserProfile has rotated since
        # the session was created (TLS fingerprint must match HTTP headers).
        if self._session is not None and not self._session_closed:
            current_target = self._get_impersonation_target()
            if current_target != self._session_impersonation_target:
                await self.close_session()

        # Invalidate the session if the proxy has changed.
        if self._session is not None and not self._session_closed:
            if proxy_url != self._session_proxy_url:
                await self.close_session()

        if self._session is None or self._session_closed:
            # Get timeout from club if available, otherwise use default
            timeout_value = getattr(self.club, "timeout", 30) if hasattr(self.club, "timeout") else 30
            session_headers = self._build_session_headers(headers)
            impersonation_target = self._get_impersonation_target()

            session_kwargs = dict(
                impersonate=impersonation_target,
                timeout=timeout_value,
                headers=session_headers,
            )
            if proxy_url is not None:
                session_kwargs["proxy"] = proxy_url

            self._session = AsyncSession(**session_kwargs)
            self._session_closed = False
            self._session_impersonation_target = impersonation_target
            self._session_proxy_url = proxy_url

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

    def _get_impersonation_target(self) -> str:
        """Return the curl-cffi impersonation target for this club's domain.

        Reads the active BrowserProfile from the rate limiter (if available)
        so the TLS fingerprint matches the HTTP headers built from that profile.
        Falls back to ``"chrome124"`` when no limiter or profile is active.
        """
        limiter = getattr(self, "rate_limiter", None)
        if limiter is None:
            return "chrome124"
        get_profile = getattr(limiter, "get_domain_profile", None)
        if not callable(get_profile):
            return "chrome124"
        try:
            domain = getattr(self.club, "scraping_domain", None)
            if not domain:
                scraping_url = getattr(self.club, "scraping_url", "") or ""
                if "://" in scraping_url:
                    domain = scraping_url.split("://", 1)[1].split("/")[0].lower()
                else:
                    domain = scraping_url.split("/")[0].lower()
            profile = get_profile(domain)
            if profile is not None:
                return profile.impersonation_target
        except Exception:
            pass
        return "chrome124"

    def _get_default_headers(self) -> Dict[str, str]:
        """
        Get default headers for this scraper type.
        Override in subclasses for specific header requirements.

        Returns:
            Default headers dictionary
        """
        return BaseHeaders.get_headers()

    async def close_session(self):
        """Close the curl_cffi session if it exists."""
        if self._session is not None and not self._session_closed:
            await self._session.close()
            self._session_closed = True
            self._session = None
            self._session_impersonation_target = None
            self._session_proxy_url = None
            self._default_headers = None

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
