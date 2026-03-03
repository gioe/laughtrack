"""
Standardized HTTP utilities for venue scrapers.

This module provides common HTTP patterns with consistent error handling,
logging, and URL normalization.
"""

from typing import Dict, Optional

import aiohttp

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
        session: aiohttp.ClientSession,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
    ) -> Optional[str]:
        """
        Fetch HTML content from a URL with standardized error handling.

        Args:
            session: Aiohttp session to use for the request
            url: URL to fetch (will be normalized)
            headers: Optional headers to include
            logger_context: Context for logging

        Returns:
            HTML content as string, or None if fetch failed
        """
        logger_context = logger_context or {}

        try:
            # Normalize URL to ensure proper scheme
            normalized_url = URLUtils.normalize_url(url)

            async with session.get(normalized_url, headers=headers) as response:
                if response.status != 200:
                    Logger.warn(f"HTTP {response.status} when fetching {normalized_url}", logger_context)
                    return None

                return await response.text()

        except Exception as e:
            return None

    @staticmethod
    async def fetch_json(
        session: aiohttp.ClientSession,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        logger_context: Optional[JSONDict] = None,
    ) -> Optional[JSONDict]:
        """
        Fetch JSON data from a URL with standardized error handling.

        Args:
            session: Aiohttp session to use for the request
            url: URL to fetch (will be normalized)
            headers: Optional headers to include
            logger_context: Context for logging

        Returns:
            JSON data as dictionary, or None if fetch failed
        """
        logger_context = logger_context or {}

        try:
            # Normalize URL to ensure proper scheme
            normalized_url = URLUtils.normalize_url(url)

            async with session.get(normalized_url, headers=headers) as response:
                if response.status != 200:
                    Logger.warn(f"HTTP {response.status} when fetching {normalized_url}", logger_context)
                    return None

                return await response.json()

        except Exception as e:
            return None
