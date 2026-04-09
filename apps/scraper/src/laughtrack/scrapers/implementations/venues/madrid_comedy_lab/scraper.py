"""
Madrid Comedy Lab scraper following the 5-component architecture.

Madrid Comedy Lab (Madrid, Spain) publishes events via the Fienta ticketing
platform API:

  https://fienta.com/api/v1/public/events?organizer=24814

The API returns all upcoming events for the organizer in a single pageless
response.

Pipeline:
  1. collect_scraping_targets() -> single Fienta API URL
  2. get_data(url)              -> fetches JSON, extracts MadridComedyLabEvent objects
  3. transformation_pipeline    -> MadridComedyLabEvent.to_show() -> Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import MadridComedyLabPageData
from .extractor import MadridComedyLabEventExtractor
from .transformer import MadridComedyLabEventTransformer

_FIENTA_API_URL = "https://fienta.com/api/v1/public/events?organizer=24814"


class MadridComedyLabScraper(BaseScraper):
    """Scraper for Madrid Comedy Lab via Fienta organizer API."""

    key = "madrid_comedy_lab"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            MadridComedyLabEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the single Fienta API endpoint."""
        Logger.info(
            f"{self._log_prefix}: targeting Fienta organizer API",
            self.logger_context,
        )
        return [_FIENTA_API_URL]

    async def get_data(self, url: str) -> Optional[MadridComedyLabPageData]:
        """Fetch and parse Fienta API response.

        Args:
            url: Fienta organizer events API URL.

        Returns:
            :class:`MadridComedyLabPageData` with extracted events, or ``None``
            when the API returns no events.
        """
        try:
            data = await self.fetch_json(url)
            if not data:
                Logger.info(
                    f"{self._log_prefix}: no data from Fienta API",
                    self.logger_context,
                )
                return None

            events = MadridComedyLabEventExtractor.parse_events(
                data, self.logger_context
            )
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events parsed from Fienta API",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: {len(events)} events from Fienta API",
                self.logger_context,
            )
            return MadridComedyLabPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching Fienta API: {e}",
                self.logger_context,
            )
            return None
