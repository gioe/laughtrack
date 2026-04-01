"""
Dynasty Typewriter scraper implementation.

Dynasty Typewriter (Los Angeles, CA) lists shows via the SquadUp ticketing platform.
Events are fetched directly from the SquadUp JSON API using the venue's user ID (7408591).
The API returns all upcoming events in a single response — no pagination needed.

The SquadUp API is protected by Cloudflare.  A bare curl_cffi Chrome impersonation
request (no application-level headers) passes the TLS fingerprint check.  Adding
headers such as Referer or Accept triggers a 403.
"""

from typing import List, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import DynastyTypewriterPageData
from .extractor import DynastyTypewriterExtractor
from .transformer import DynastyTypewriterEventTransformer

_SQUADUP_API_URL = (
    "https://www.squadup.com/api/v3/events"
    "?user_ids=7408591"
    "&page_size=100"
    "&topics_exclude=true"
    "&additional_attr=sold_out"
    "&include=custom_fields"
)


class DynastyTypewriterScraper(BaseScraper):
    """
    Scraper for Dynasty Typewriter (dynastytypewriter.com).

    Fetches upcoming events from the SquadUp API using the venue's user ID.
    Uses bare Chrome impersonation (no extra headers) to bypass Cloudflare protection.
    """

    key = "dynasty_typewriter"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(DynastyTypewriterEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the single SquadUp API URL."""
        return [_SQUADUP_API_URL]

    async def get_data(self, url: str) -> Optional[DynastyTypewriterPageData]:
        """
        Fetch events from the SquadUp API and return extracted DynastyTypewriterEvents.

        Uses a bare AsyncSession with Chrome impersonation and no application-level
        headers to pass Cloudflare's TLS fingerprint check.

        Args:
            url: The SquadUp API URL (from collect_scraping_targets)

        Returns:
            DynastyTypewriterPageData containing events, or None if no events found
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            async with AsyncSession(impersonate="chrome124") as session:
                response = await session.get(url)

            if response.status_code != 200:
                Logger.warn(
                    f"{self._log_prefix}: HTTP {response.status_code} from {url}",
                    self.logger_context,
                )
                return None

            data = response.json()
            events = DynastyTypewriterExtractor.extract_events(data)

            if not events:
                Logger.info(f"{self._log_prefix}: no events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return DynastyTypewriterPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None
