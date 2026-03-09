"""
Standardized HTTP utilities for venue scrapers.

This module provides common HTTP patterns with consistent error handling,
logging, and URL normalization.
"""

from typing import Dict, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.url import URLUtils


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
    ) -> Optional[str]:
        """
        Fetch HTML content from a URL with standardized error handling.

        Args:
            session: curl_cffi AsyncSession to use for the request
            url: URL to fetch (will be normalized)
            headers: Optional headers to include
            logger_context: Context for logging

        Returns:
            HTML content as string, or None if the response status is not 200.

        Raises:
            Exception: Any network or connection error is re-raised so callers
                can log and handle it (avoids duplicate log entries).
        """
        logger_context = logger_context or {}

        try:
            # Normalize URL to ensure proper scheme
            normalized_url = URLUtils.normalize_url(url)

            response = await session.get(normalized_url, headers=headers)
            if response.status_code != 200:
                Logger.warn(f"HTTP {response.status_code} when fetching {normalized_url}", logger_context)
                return None

            return response.text

        except Exception:
            raise

    @staticmethod
    async def fetch_json(
        session: AsyncSession,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
    ) -> Optional[JSONDict]:
        """
        Fetch JSON data from a URL with standardized error handling.

        Args:
            session: curl_cffi AsyncSession to use for the request
            url: URL to fetch (will be normalized)
            headers: Optional headers to include
            logger_context: Context for logging

        Returns:
            JSON data as dictionary, or None if the response status is not 200.

        Raises:
            Exception: Any network or connection error is re-raised so callers
                can log and handle it (avoids duplicate log entries).
        """
        logger_context = logger_context or {}

        try:
            # Normalize URL to ensure proper scheme
            normalized_url = URLUtils.normalize_url(url)

            response = await session.get(normalized_url, headers=headers)
            if response.status_code != 200:
                Logger.warn(f"HTTP {response.status_code} when fetching {normalized_url}", logger_context)
                return None

            return response.json()

        except Exception:
            raise
