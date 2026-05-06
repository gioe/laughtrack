"""TK's scraper for the current static public events page."""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import TksComedyPageData
from .extractor import TksComedyExtractor
from .transformer import TksComedyEventTransformer


class TksComedyScraper(BaseScraper):
    """Scraper for TK's static Spothopper events page."""

    key = "tks_comedy"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TksComedyEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[TksComedyPageData]:
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(f"{self._log_prefix}: empty response for {url}", self.logger_context)
                return None

            events = TksComedyExtractor.extract_events(html)
            if not events:
                Logger.info(f"{self._log_prefix}: no comedy events found on {url}", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: extracted {len(events)} event(s) from {url}", self.logger_context)
            return TksComedyPageData(event_list=events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: error fetching {url}: {e}", self.logger_context)
            return None
