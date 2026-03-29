"""
Goofs Comedy Club scraper implementation.

Goofs Comedy Club (432 McGrath Highway, Somerville, MA) runs a custom
Next.js ticketing platform at goofscomedy.com.  All upcoming shows are
rendered server-side on the /p/shows listing page as a Next.js RSC
flight payload, so a single HTTP request is sufficient.

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single page)
  2. get_data(url) → fetch /p/shows HTML → extract GoofsEvents
  3. transformation_pipeline → GoofsEvent.to_show() → Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import GoofsPageData
from .extractor import GoofsEventExtractor
from .transformer import GoofsEventTransformer


class GoofsComedyClubScraper(BaseScraper):
    """Scraper for Goofs Comedy Club (Somerville, MA)."""

    key = "goofs"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(GoofsEventTransformer(club))

    async def get_data(self, url: str) -> Optional[GoofsPageData]:
        """Fetch the /p/shows listing page and extract all upcoming shows."""
        try:
            normalized_url = URLUtils.normalize_url(url)
            Logger.info(f"{self.__class__.__name__} [{self._club.name}]: fetching shows page: {normalized_url}", self.logger_context)

            html = await self.fetch_html(normalized_url)
            if not html:
                Logger.warn(f"{self.__class__.__name__} [{self._club.name}]: empty HTML from shows page", self.logger_context)
                return None

            events = GoofsEventExtractor.extract_shows(html)
            if not events:
                Logger.warn(f"{self.__class__.__name__} [{self._club.name}]: no shows extracted from page", self.logger_context)
                return None

            Logger.info(f"{self.__class__.__name__} [{self._club.name}]: extracted {len(events)} shows", self.logger_context)
            return GoofsPageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self.__class__.__name__} [{self._club.name}]: error scraping page {url}: {e}", self.logger_context)
            return None
