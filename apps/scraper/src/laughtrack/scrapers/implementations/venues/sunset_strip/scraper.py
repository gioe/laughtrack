"""
Sunset Strip Comedy Club scraper implementation.

Sunset Strip Comedy Club (214 E 6th Street, Austin TX) is a 21+ comedy club
co-hosted by Kill Tony's co-host, running several weekly shows.  Shows are
ticketed through SquadUP and fetched via:

  GET https://www.squadup.com/api/v3/events
      ?user_ids=9086799&page_size=100&include=custom_fields&page=<N>

The SquadUP site is protected by Cloudflare.  A bare curl_cffi Chrome
impersonation request (no application headers) passes the TLS fingerprint
check.  Adding standard scraper headers triggers a 403.

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (base class default)
  2. get_data(url)              → fetches all SquadUP event pages and returns
                                  SunsetStripPageData
  3. transformation_pipeline   → SquadUpEvent.to_show() → Show objects
"""

from typing import Any, Dict, List, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import SunsetStripEventExtractor
from .page_data import SunsetStripPageData
from .transformer import SunsetStripEventTransformer

_SQUADUP_EVENTS_URL = "https://www.squadup.com/api/v3/events"
_SQUADUP_USER_ID = "9086799"
_PAGE_SIZE = 100
_MAX_PAGES = 20


class SunsetStripScraper(BaseScraper):
    """
    Scraper for Sunset Strip Comedy Club (Austin, TX).

    Fetches upcoming shows from the SquadUP API using bare Chrome impersonation
    to bypass Cloudflare protection.  No application-level HTTP headers are sent.
    """

    key = "sunset_strip"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            SunsetStripEventTransformer(club)
        )

    async def _fetch_events_page(self, page: int) -> Optional[Dict[str, Any]]:
        """
        Fetch one page of events from the SquadUP API.

        Uses a bare AsyncSession (no extra headers) to avoid triggering
        Cloudflare's bot detection.

        Args:
            page: 1-based page number.

        Returns:
            Parsed JSON dict, or None on failure.
        """
        params = (
            f"user_ids={_SQUADUP_USER_ID}"
            f"&page_size={_PAGE_SIZE}"
            f"&include=custom_fields"
            f"&page={page}"
        )
        url = f"{_SQUADUP_EVENTS_URL}?{params}"
        try:
            async with AsyncSession(impersonate="chrome124") as session:
                response = await session.get(url)
                if response.status_code != 200:
                    Logger.warn(
                        f"SunsetStripScraper: HTTP {response.status_code} fetching page {page}",
                        self.logger_context,
                    )
                    return None
                return response.json()
        except Exception as e:
            Logger.error(
                f"SunsetStripScraper: error fetching page {page}: {e}",
                self.logger_context,
            )
            return None

    async def get_data(self, url: str) -> Optional[SunsetStripPageData]:
        """
        Fetch all upcoming shows from the SquadUP API (paginated) and extract events.

        The ``url`` argument (from ``club.scraping_url``) is ignored in favour of
        the hard-coded SquadUP API endpoint, which is the authoritative data source.

        Args:
            url: Unused; the club's scraping URL for logging context only.

        Returns:
            SunsetStripPageData containing all events, or None if none found.
        """
        all_events: List = []
        seen_ids: set = set()
        total_pages: Optional[int] = None

        for page in range(1, _MAX_PAGES + 1):
            if total_pages is not None and page > total_pages:
                break

            data = await self._fetch_events_page(page)
            if not data:
                break

            # Discover total page count from first response
            if total_pages is None:
                try:
                    total_pages = int(
                        data.get("meta", {}).get("paging", {}).get("total_pages", 1)
                    )
                except (TypeError, ValueError):
                    total_pages = 1

            raw_events: List[Dict[str, Any]] = data.get("events") or []
            if not raw_events:
                break

            events = SunsetStripEventExtractor.extract_shows(raw_events)
            Logger.debug(
                f"SunsetStripScraper: page {page}/{total_pages}: "
                f"{len(events)} events extracted",
                self.logger_context,
            )

            for event in events:
                if event.event_id not in seen_ids:
                    seen_ids.add(event.event_id)
                    all_events.append(event)

        if not all_events:
            Logger.info(
                f"SunsetStripScraper: no events found (user_id={_SQUADUP_USER_ID})",
                self.logger_context,
            )
            return None

        Logger.info(
            f"SunsetStripScraper: extracted {len(all_events)} events total",
            self.logger_context,
        )
        return SunsetStripPageData(event_list=all_events)
