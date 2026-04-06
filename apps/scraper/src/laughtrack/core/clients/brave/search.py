"""Brave Search API client.

Wraps the Brave Web Search API for finding comedian websites.
Free tier: ~1,000 queries/month.
"""

import os
import time
from typing import List

import requests

from laughtrack.core.clients.google.custom_search import SearchResult
from laughtrack.foundation.infrastructure.logger.logger import Logger

_API_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchClient:
    """Client for Brave Web Search API."""

    def __init__(self):
        self._api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
        self._queries_used = 0
        try:
            self._daily_limit = int(os.environ.get("BRAVE_SEARCH_DAILY_LIMIT", "33"))
        except ValueError:
            self._daily_limit = 33
        try:
            self._delay_s = float(os.environ.get("BRAVE_SEARCH_DELAY_S", "1.0"))
        except ValueError:
            self._delay_s = 1.0

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def queries_remaining(self) -> int:
        return max(0, self._daily_limit - self._queries_used)

    @property
    def source_name(self) -> str:
        return "brave_search"

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Execute a search query and return results.

        Returns an empty list on any error (network, auth, quota).
        """
        if not self.is_configured:
            Logger.warn("Brave Search not configured — set BRAVE_SEARCH_API_KEY")
            return []

        if self._queries_used >= self._daily_limit:
            Logger.warn(f"Brave Search daily limit reached ({self._daily_limit} queries)")
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }

        params = {
            "q": query,
            "count": min(num_results, 20),
        }

        try:
            if self._delay_s > 0:
                time.sleep(self._delay_s)

            resp = requests.get(_API_URL, headers=headers, params=params, timeout=10)
            self._queries_used += 1

            if resp.status_code == 429:
                Logger.warn("Brave Search rate limited (HTTP 429)")
                return []

            if resp.status_code != 200:
                Logger.warn(f"Brave Search HTTP {resp.status_code}: {resp.text[:200]}")
                return []

            data = resp.json()
            items = data.get("web", {}).get("results", [])

            return [
                SearchResult(
                    title=item.get("title", ""),
                    link=item.get("url", ""),
                    snippet=item.get("description", ""),
                    display_link=item.get("url", ""),
                )
                for item in items
            ]

        except requests.RequestException as e:
            Logger.warn(f"Brave Search request failed: {e}")
            return []
        except (ValueError, KeyError) as e:
            Logger.warn(f"Brave Search response parse error: {e}")
            return []
