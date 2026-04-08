"""
Largo at the Coronet scraper.

Single-page scraper for largo-la.com. All event data (title, date,
time, price, ticket URL) is available on the homepage — no per-event
detail fetching is needed.

Uses WordPress custom post type event_listing with SeeTickets links.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import LargoAtTheCoronetPageData
from .extractor import LargoAtTheCoronetExtractor
from .transformer import LargoAtTheCoronetEventTransformer


class LargoAtTheCoronetScraper(BaseScraper):
    """
    Scraper for Largo at the Coronet (largo-la.com).

    All event data is extracted from the single homepage listing.
    """

    key = "largo_at_the_coronet"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LargoAtTheCoronetEventTransformer(club))

    async def discover_urls(self) -> List[str]:
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[LargoAtTheCoronetPageData]:
        try:
            normalized_url = URLUtils.normalize_url(url)
            html = await self.fetch_html(normalized_url)

            if not html:
                Logger.warn(f"{self._log_prefix}: No HTML returned from {normalized_url}", self.logger_context)
                return None

            events = LargoAtTheCoronetExtractor.extract_events(html)

            if not events:
                Logger.warn(f"{self._log_prefix}: No events found on {normalized_url}", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: Extracted {len(events)} events", self.logger_context)
            return LargoAtTheCoronetPageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error in get_data: {e}", self.logger_context)
            return None
