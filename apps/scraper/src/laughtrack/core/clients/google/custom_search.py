"""Google Custom Search JSON API client.

Wraps the Custom Search API for finding comedian websites.
Free tier: 100 queries/day.
"""

import os
import time
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

import requests

from laughtrack.foundation.infrastructure.logger.logger import Logger

_API_URL = "https://www.googleapis.com/customsearch/v1"

# Domains to exclude — social media, ticketing, reference sites
_EXCLUDED_DOMAINS = frozenset({
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "linkedin.com",
    "reddit.com",
    "wikipedia.org",
    "imdb.com",
    "ticketmaster.com",
    "eventbrite.com",
    "axs.com",
    "seatgeek.com",
    "stubhub.com",
    "livenation.com",
    "songkick.com",
    "bandsintown.com",
    "spotify.com",
    "apple.com",
    "soundcloud.com",
    "myspace.com",
    "pinterest.com",
    "tumblr.com",
    "yelp.com",
    "tripadvisor.com",
    # Venue / comedy directory listing sites
    "improv.com",
    "improvtx.com",
    "levitylive.com",
    "dead-frog.com",
    "thecomedystore.com",
    "laughfactory.com",
    "gothamcomedyclub.com",
    "cellardog.com",
    "comedycellar.com",
    "standuplive.com",
    # Streaming / media sites
    "netflix.com",
    "hulu.com",
    "hbo.com",
    "max.com",
    "primevideo.com",
    "peacocktv.com",
    # Ticketing resellers
    "vividseats.com",
    # Venue listing / arts center sites
    "comedyworks.com",
    "mgmresorts.com",
    "mayoarts.org",
    # Reference / media / press sites
    "tvinsider.com",
    "kennedy-center.org",
    "fasterthannormal.com",
    "famousbirthdays.com",
    "tvguide.com",
    "rottentomatoes.com",
    "tmz.com",
    "people.com",
    "variety.com",
    "hollywoodreporter.com",
    "deadline.com",
})


@dataclass
class SearchResult:
    """A single Google Custom Search result."""

    title: str
    link: str
    snippet: str
    display_link: str


class GoogleCustomSearchClient:
    """Client for Google Custom Search JSON API."""

    def __init__(self):
        self._api_key = os.environ.get("GOOGLE_CUSTOM_SEARCH_API_KEY", "")
        self._engine_id = os.environ.get("GOOGLE_CUSTOM_SEARCH_ENGINE_ID", "")
        self._queries_today = 0
        try:
            self._daily_limit = int(os.environ.get("GOOGLE_CUSTOM_SEARCH_DAILY_LIMIT", "100"))
        except ValueError:
            self._daily_limit = 100
        try:
            self._delay_s = float(os.environ.get("GOOGLE_CUSTOM_SEARCH_DELAY_S", "0.5"))
        except ValueError:
            self._delay_s = 0.5

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._engine_id)

    @property
    def source_name(self) -> str:
        return "google_search"

    @property
    def queries_remaining(self) -> int:
        return max(0, self._daily_limit - self._queries_today)

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Execute a search query and return results.

        Returns an empty list on any error (network, auth, quota).
        """
        if not self.is_configured:
            Logger.warn("Google Custom Search not configured — set GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
            return []

        if self._queries_today >= self._daily_limit:
            Logger.warn(f"Google Custom Search daily limit reached ({self._daily_limit} queries)")
            return []

        params = {
            "key": self._api_key,
            "cx": self._engine_id,
            "q": query,
            "num": min(num_results, 10),
        }

        try:
            if self._delay_s > 0:
                time.sleep(self._delay_s)

            resp = requests.get(_API_URL, params=params, timeout=10)
            self._queries_today += 1

            if resp.status_code == 429:
                Logger.warn("Google Custom Search rate limited (HTTP 429)")
                return []

            if resp.status_code != 200:
                Logger.warn(f"Google Custom Search HTTP {resp.status_code}: {resp.text[:200]}")
                return []

            data = resp.json()
            items = data.get("items", [])

            return [
                SearchResult(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    display_link=item.get("displayLink", ""),
                )
                for item in items
            ]

        except requests.RequestException as e:
            Logger.warn(f"Google Custom Search request failed: {e}")
            return []
        except (ValueError, KeyError) as e:
            Logger.warn(f"Google Custom Search response parse error: {e}")
            return []

    @staticmethod
    def is_excluded_domain(url: str) -> bool:
        """Check if a URL belongs to an excluded domain."""
        try:
            hostname = urlparse(url).hostname or ""
            # Strip www. prefix for comparison
            hostname = hostname.lower().removeprefix("www.")
            return any(hostname == d or hostname.endswith("." + d) for d in _EXCLUDED_DOMAINS)
        except Exception:
            return False
