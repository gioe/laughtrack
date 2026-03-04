"""
Rate limiting infrastructure for coordinating scraping across multiple domains.

This module provides a singleton RateLimiter that ensures domain-wide rate limiting
coordination across all scrapers, preventing overwhelming target servers.
"""

import asyncio
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from laughtrack.foundation.models.types import ScrapingTarget


class RateLimiter:
    """
    Singleton rate limiter that coordinates requests across all scrapers.

    Provides both sync and async interfaces for rate limiting with domain-specific
    limits and global coordination.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._domain_limits: Dict[str, float] = {}  # domain -> requests per second
        self._domain_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._async_domain_locks: Dict[str, asyncio.Lock] = {}
        self._last_request: Dict[str, float] = {}
        self._global_lock = threading.Lock()

        # Default rate limits (requests per second)
        self._default_limits = {
            "eventbrite.com": 0.5,  # 1 request per 2 seconds
            "comedycellar.com": 1.0,  # 1 request per second
            "thestandnyc.com": 1.0,
            "eastvillecomedy.com": 2.0,  # 1 request per 0.5 seconds
            "default": 1.0,  # Default 1 request per second
        }

        self._domain_limits.update(self._default_limits)
        self._initialized = True

    def set_domain_limit(self, domain: str, rate_limit: float) -> None:
        """Set the rate limit for a specific domain."""
        with self._global_lock:
            self._domain_limits[domain] = rate_limit

    def get_domain_limit(self, domain: str) -> float:
        """Get the rate limit for a domain."""
        return self._domain_limits.get(domain, self._domain_limits["default"])

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting."""
        if "://" in url:
            url = url.split("://", 1)[1]
        domain = url.split("/")[0]
        return domain.lower()

    def _is_url(self, target: str) -> bool:
        """Check if the target is a URL or just an identifier string."""
        return target.startswith(("http://", "https://")) or "." in target

    def _should_wait(self, domain: str) -> Optional[float]:
        """
        Check if we should wait before making a request to this domain.
        Returns the wait time in seconds, or None if no wait is needed.
        """
        limit = self.get_domain_limit(domain)
        min_interval = 1.0 / limit

        now = time.time()
        last_request = self._last_request.get(domain, 0)

        time_since_last = now - last_request
        if time_since_last < min_interval:
            return min_interval - time_since_last

        return None

    def wait_if_needed(self, url: str) -> None:
        """
        Synchronous rate limiting. Blocks if necessary to respect rate limits.

        Args:
            url: The URL being requested (domain will be extracted) or identifier string
        """
        # Check if target is actually a URL, not just an identifier string
        if not self._is_url(url):
            return

        domain = self._extract_domain(url)

        with self._domain_locks[domain]:
            wait_time = self._should_wait(domain)
            if wait_time:
                time.sleep(wait_time)

            self._last_request[domain] = time.time()

    def _get_async_lock(self, domain: str) -> asyncio.Lock:
        """Get or create a per-domain asyncio.Lock for the async rate-limiting path."""
        if domain not in self._async_domain_locks:
            self._async_domain_locks[domain] = asyncio.Lock()
        return self._async_domain_locks[domain]

    async def await_if_needed(self, target: ScrapingTarget) -> None:
        """
        Asynchronous rate limiting. Awaits if necessary to respect rate limits.

        Args:
            target: The URL being requested (domain will be extracted) or identifier string
        """
        # Check if target is actually a URL, not just an identifier string
        if not self._is_url(target):
            return

        domain = self._extract_domain(target)

        async with self._get_async_lock(domain):
            wait_time = self._should_wait(domain)
            if wait_time:
                await asyncio.sleep(wait_time)

            self._last_request[domain] = time.time()

    def get_stats(self) -> Dict[str, Dict]:
        """Get rate limiting statistics for monitoring."""
        with self._global_lock:
            stats = {}
            for domain, limit in self._domain_limits.items():
                last_request = self._last_request.get(domain, 0)
                stats[domain] = {
                    "limit_rps": limit,
                    "last_request": datetime.fromtimestamp(last_request) if last_request else None,
                    "time_since_last": time.time() - last_request if last_request else None,
                }
            return stats

    def reset_domain(self, domain: str) -> None:
        """Reset rate limiting state for a domain."""
        with self._domain_locks[domain]:
            self._last_request.pop(domain, None)


# Global rate limiter instance
rate_limiter = RateLimiter()
