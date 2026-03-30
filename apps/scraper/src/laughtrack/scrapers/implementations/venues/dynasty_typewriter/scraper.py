"""
Dynasty Typewriter scraper implementation.

Dynasty Typewriter (Los Angeles, CA) lists shows via the SquadUp ticketing platform.
Events are fetched directly from the SquadUp JSON API using the venue's user ID (7408591).
The API returns all upcoming events in a single response — no pagination needed.

The request requires a Referer header pointing to the Dynasty Typewriter website so
the SquadUp API accepts the cross-origin request.
"""

from typing import List, Optional

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
_REFERER = "https://www.dynastytypewriter.com/"


class DynastyTypewriterScraper(BaseScraper):
    """
    Scraper for Dynasty Typewriter (dynastytypewriter.com).

    Fetches upcoming events from the SquadUp API using the venue's user ID.
    A Referer header is required for the API to accept requests.
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

        Args:
            url: The SquadUp API URL (from collect_scraping_targets)

        Returns:
            DynastyTypewriterPageData containing events, or None if no events found
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            response = await self.fetch_json(url, headers={"Referer": _REFERER})
            if not response:
                Logger.info(f"{self._log_prefix}: no response from {url}", self.logger_context)
                return None

            events = DynastyTypewriterExtractor.extract_events(response)

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
