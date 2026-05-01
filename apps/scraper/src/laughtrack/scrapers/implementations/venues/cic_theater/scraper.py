"""Custom scraper for CIC Theater's recurring public schedule."""

from datetime import date
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import CicTheaterPageData
from .extractor import CicTheaterExtractor
from .transformer import CicTheaterEventTransformer


class CicTheaterScraper(BaseScraper):
    """Scrape CIC Theater's weekly public shows from the Browse All Shows page."""

    key = "cic_theater"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(CicTheaterEventTransformer(club))

    def collect_scraping_targets_sync(self) -> List[ScrapingTarget]:
        return [self.club.scraping_url or "https://www.cictheater.com/browse-shows"]

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        return self.collect_scraping_targets_sync()

    @staticmethod
    def _today() -> date:
        return date.today()

    async def get_data(self, url: str) -> Optional[CicTheaterPageData]:
        try:
            html = await self.fetch_html(url)
        except Exception as e:
            Logger.warn(f"{self._log_prefix}: failed to fetch CIC Theater page {url}: {e}", self.logger_context)
            return None

        events = CicTheaterExtractor.extract_events(
            html or "",
            source_url=url,
            today=self._today(),
        )
        if not events:
            Logger.info(f"{self._log_prefix}: no recurring CIC Theater shows found", self.logger_context)
            return None

        return CicTheaterPageData(event_list=events)

