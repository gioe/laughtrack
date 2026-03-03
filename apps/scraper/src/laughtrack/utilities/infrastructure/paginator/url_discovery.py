"""
URL discovery patterns and utilities for scrapers.

This module provides standardized URL discovery patterns for different
types of venues, including calendar pages, API endpoints, and paginated content.
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import aiohttp

from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger


class UrlDiscoveryStrategy(ABC):
    """Abstract base class for URL discovery strategies."""

    @abstractmethod
    async def discover_urls(self, base_url: str, session: aiohttp.ClientSession) -> List[str]:
        """Discover URLs from a base URL."""


class StaticUrlStrategy(UrlDiscoveryStrategy):
    """Strategy for venues with static URLs (no discovery needed)."""

    async def discover_urls(self, base_url: str, session: aiohttp.ClientSession) -> List[str]:
        """Return the base URL as-is."""
        return [base_url]


class PaginationUrlStrategy(UrlDiscoveryStrategy):
    """Strategy for paginated content discovery."""

    def __init__(self, max_pages: int = 10, page_param: str = "page"):
        self.max_pages = max_pages
        self.page_param = page_param

    async def discover_urls(self, base_url: str, session: aiohttp.ClientSession) -> List[str]:
        """Discover paginated URLs."""
        urls = []
        visited = set()
        current_url = base_url
        page_count = 0

        while current_url and page_count < self.max_pages and current_url not in visited:
            visited.add(current_url)
            urls.append(current_url)

            try:
                async with session.get(current_url) as response:
                    response.raise_for_status()
                    content = await response.text()

                    # Find next page URL
                    next_url = self._find_next_page_url(content, current_url)
                    current_url = next_url
                    page_count += 1

            except Exception as e:
                Logger.warn(f"Error discovering paginated URLs: {e}")
                break

        return urls

    def _find_next_page_url(self, html_content: str, base_url: str) -> Optional[str]:
        """Find the next page URL from HTML content."""
        # Common next page patterns
        next_patterns = [
            {"tag": "a", "attrs": {"class": re.compile(r"next|more|continue", re.I)}},
            {"tag": "a", "attrs": {"id": re.compile(r"next|more", re.I)}},
            {"tag": "a", "text": re.compile(r"next|more|continue|\u00bb|\u203a", re.I)},
            {"tag": "link", "attrs": {"rel": "next"}},
        ]

        for pattern in next_patterns:
            try:
                elements = HtmlScraper.find_elements_with_patterns(
                    html_content, pattern["tag"], attrs=pattern.get("attrs", {})
                )

                for element in elements:
                    # Check text pattern if specified
                    if "text" in pattern:
                        if not element.text or not pattern["text"].search(element.text):
                            continue

                    href = element.get("href")
                    if href:
                        return urljoin(base_url, href)
            except Exception:
                # Continue trying other patterns if this one fails
                continue

        return None


class CalendarUrlStrategy(UrlDiscoveryStrategy):
    """Strategy for calendar-based URL discovery."""

    def __init__(self, months_ahead: int = 3):
        self.months_ahead = months_ahead

    async def discover_urls(self, base_url: str, session: aiohttp.ClientSession) -> List[str]:
        """Discover calendar URLs for upcoming months."""
        from datetime import datetime, timedelta

        urls = [base_url]  # Include base URL

        # Generate URLs for upcoming months
        current_date = datetime.now()

        for month_offset in range(1, self.months_ahead + 1):
            # Calculate target date
            target_date = current_date + timedelta(days=30 * month_offset)
            year = target_date.year
            month = target_date.month

            # Generate common calendar URL patterns
            calendar_patterns = [
                f"{base_url}?year={year}&month={month}",
                f"{base_url}?date={year}-{month:02d}",
                f"{base_url}/{year}/{month:02d}",
                f"{base_url}?calendar={year}-{month:02d}-01",
            ]

            urls.extend(calendar_patterns)

        return urls


class ApiEndpointDiscoveryStrategy(UrlDiscoveryStrategy):
    """Strategy for discovering API endpoints from web pages."""

    def __init__(self, endpoint_patterns: Optional[List[str]] = None):
        self.endpoint_patterns = endpoint_patterns or [
            r"api/events",
            r"api/shows",
            r"graphql",
            r"api/calendar",
            r"api/lineup",
        ]

    async def discover_urls(self, base_url: str, session: aiohttp.ClientSession) -> List[str]:
        """Discover API endpoints from page source."""
        try:
            async with session.get(base_url) as response:
                response.raise_for_status()
                content = await response.text()

                # Extract API endpoints from JavaScript and HTML
                endpoints = self._extract_api_endpoints(content, base_url)

                return endpoints if endpoints else [base_url]

        except Exception as e:
            Logger.warn(f"Error discovering API endpoints: {e}")
            return [base_url]

    def _extract_api_endpoints(self, content: str, base_url: str) -> List[str]:
        """Extract API endpoints from page content."""
        endpoints = []

        # Look for API endpoints in JavaScript
        js_patterns = [
            r'["\']([^"\']*api[^"\']*)["\']',
            r'["\']([^"\']*graphql[^"\']*)["\']',
            r'fetch\s*\(\s*["\']([^"\']+)["\']',
            r'axios\s*\.\s*\w+\s*\(\s*["\']([^"\']+)["\']',
        ]

        for pattern in js_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if any(endpoint_pattern in match.lower() for endpoint_pattern in self.endpoint_patterns):
                    full_url = urljoin(base_url, match)
                    endpoints.append(full_url)

        # Look for API endpoints in HTML attributes
        # Check data attributes
        try:
            elements_with_data_api = HtmlScraper.find_elements(content, "data-api-url")
            for element in elements_with_data_api:
                api_url = element.get("data-api-url")
                if api_url:
                    endpoints.append(urljoin(base_url, api_url))
        except Exception:
            pass

        # Check form actions
        try:
            forms = HtmlScraper.find_elements(content, "form")
            for form in forms:
                action = form.get("action", "")
                if any(pattern in action.lower() for pattern in self.endpoint_patterns):
                    endpoints.append(urljoin(base_url, action))
        except Exception:
            pass

        return list(set(endpoints))  # Remove duplicates


class UrlDiscoveryManager:
    """Manages URL discovery using different strategies."""

    def __init__(self):
        self.strategies: Dict[str, UrlDiscoveryStrategy] = {}
        self.url_cache: Dict[str, List[str]] = {}
        self.cache_ttl = 3600  # 1 hour
        self.cache_timestamps: Dict[str, float] = {}

    def register_strategy(self, name: str, strategy: UrlDiscoveryStrategy):
        """Register a URL discovery strategy."""
        self.strategies[name] = strategy

    async def discover_urls(
        self, base_url: str, session: aiohttp.ClientSession, strategy_name: str = "static", use_cache: bool = True
    ) -> List[str]:
        """
        Discover URLs using the specified strategy.

        Args:
            base_url: Base URL to discover from
            session: aiohttp session
            strategy_name: Name of strategy to use
            use_cache: Whether to use cached results

        Returns:
            List of discovered URLs
        """
        # Check cache first
        if use_cache and self._is_cached(base_url):
            return self.url_cache[base_url]

        # Get strategy
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        try:
            # Discover URLs
            urls = await strategy.discover_urls(base_url, session)

            # Cache results
            if use_cache:
                self._cache_urls(base_url, urls)

            return urls

        except Exception as e:
            Logger.error(f"URL discovery failed with strategy {strategy_name}: {e}")
            return [base_url]  # Fallback to base URL

    def _is_cached(self, base_url: str) -> bool:
        """Check if URL results are cached and still valid."""
        if base_url not in self.url_cache:
            return False

        import time

        timestamp = self.cache_timestamps.get(base_url, 0)
        return time.time() - timestamp < self.cache_ttl

    def _cache_urls(self, base_url: str, urls: List[str]):
        """Cache discovered URLs."""
        import time

        self.url_cache[base_url] = urls
        self.cache_timestamps[base_url] = time.time()

    def clear_cache(self):
        """Clear the URL cache."""
        self.url_cache.clear()
        self.cache_timestamps.clear()

    def get_available_strategies(self) -> List[str]:
        """Get list of available strategy names."""
        return list(self.strategies.keys())


# Factory function to create a pre-configured discovery manager
def create_discovery_manager() -> UrlDiscoveryManager:
    """Create a discovery manager with common strategies."""
    manager = UrlDiscoveryManager()

    # Register common strategies
    manager.register_strategy("static", StaticUrlStrategy())
    manager.register_strategy("pagination", PaginationUrlStrategy())
    manager.register_strategy("calendar", CalendarUrlStrategy())
    manager.register_strategy("api_discovery", ApiEndpointDiscoveryStrategy())

    return manager


# Helper functions for common URL patterns
class UrlPatternHelpers:
    """Helper functions for common URL patterns."""

    @staticmethod
    def is_api_endpoint(url: str) -> bool:
        """Check if URL looks like an API endpoint."""
        api_indicators = ["api", "graphql", "rest", "json", "ajax"]
        return any(indicator in url.lower() for indicator in api_indicators)

    @staticmethod
    def is_pagination_url(url: str) -> bool:
        """Check if URL contains pagination parameters."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        pagination_params = ["page", "offset", "limit", "next", "cursor"]
        return any(param in query_params for param in pagination_params)

    @staticmethod
    def extract_base_url(url: str) -> str:
        """Extract base URL without query parameters."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    @staticmethod
    def build_paginated_urls(base_url: str, max_pages: int = 10, page_param: str = "page") -> List[str]:
        """Build paginated URLs."""
        urls = []

        for page in range(1, max_pages + 1):
            separator = "&" if "?" in base_url else "?"
            paginated_url = f"{base_url}{separator}{page_param}={page}"
            urls.append(paginated_url)

        return urls
