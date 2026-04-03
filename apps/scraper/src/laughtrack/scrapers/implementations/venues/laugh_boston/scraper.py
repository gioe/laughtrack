"""
Laugh Boston scraper implementation.

Laugh Boston shows are fetched via the Pixl Calendar API
(pixlcalendar.com/api/events/laugh-boston), which returns the full event
catalogue with Tixr ticket URLs plus all the data needed to build Show objects
(title, start datetime, timezone, sales/ticket details, description).

The scraper builds TixrEvent objects directly from the Pixl API response
without fetching individual Tixr event pages. This avoids Tixr's DataDome
WAF, which blocks GitHub Actions IP ranges and caused ~50% of per-event
fetches to return HTTP 403 in the 2026-04-01 run.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import LaughBostonEventExtractor
from .data import LaughBostonPageData
from .transformer import LaughBostonEventTransformer


class LaughBostonScraper(BaseScraper):
    """
    Scraper for Laugh Boston comedy club.

    Fetches events from the Pixl Calendar API and builds TixrEvent objects
    directly from the API response — no per-event Tixr page fetches required.
    """

    key = "laugh_boston"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LaughBostonEventTransformer(club))

    async def get_data(self, url: str) -> Optional[LaughBostonPageData]:
        """
        Fetch events from the Pixl Calendar API and return TixrEvent objects.

        ``url`` is the club's scraping_url, which should point to the Pixl Calendar
        API endpoint (e.g. https://pixlcalendar.com/api/events/laugh-boston).

        Returns:
            LaughBostonPageData containing TixrEvent objects, or None if no events found
        """
        try:
            data = await self.fetch_json(url)
            if not data:
                Logger.info(f"{self._log_prefix}: No data returned from Pixl Calendar", self.logger_context)
                return None

            tixr_events = LaughBostonEventExtractor.parse_events_from_pixl(data, self.club)

            if not tixr_events:
                Logger.info(
                    f"{self._log_prefix}: No events parsed from Pixl Calendar response", self.logger_context
                )
                return None

            Logger.info(
                f"{self._log_prefix}: Parsed {len(tixr_events)} events from Pixl Calendar",
                self.logger_context,
            )
            return LaughBostonPageData(
                event_list=tixr_events,
                tixr_urls=[e.source_url for e in tixr_events],
            )

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error fetching data from Pixl Calendar: {str(e)}", self.logger_context
            )
            return None
