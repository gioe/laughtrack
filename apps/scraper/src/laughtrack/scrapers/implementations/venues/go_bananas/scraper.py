"""Custom scraper for Go Bananas Comedy Club's WordPress show listing."""

from datetime import date
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import GoBananasPageData
from .extractor import GoBananasExtractor
from .transformer import GoBananasEventTransformer


class GoBananasScraper(BaseScraper):
    """Scrape ticketed showtimes from Go Bananas' public homepage markup."""

    key = "go_bananas"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(GoBananasEventTransformer(club))

    def collect_scraping_targets_sync(self) -> List[ScrapingTarget]:
        return [self.club.scraping_url or "https://gobananascomedy.com"]

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        return self.collect_scraping_targets_sync()

    @staticmethod
    def _today() -> date:
        return date.today()

    async def get_data(self, url: str) -> Optional[GoBananasPageData]:
        try:
            html = await self.fetch_html(url)
        except Exception as e:
            Logger.warn(f"{self._log_prefix}: failed to fetch Go Bananas page {url}: {e}", self.logger_context)
            return None

        events = GoBananasExtractor.extract_events(
            html or "",
            source_url=url,
            today=self._today(),
        )
        if not events:
            Logger.info(f"{self._log_prefix}: no ticketed Go Bananas showtimes found", self.logger_context)
            return None

        return GoBananasPageData(event_list=events)
