"""Generic scraper for custom Wix/Velo _functions/shows JSON endpoints."""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.wix_functions_shows.data import (
    WixFunctionsShowsPageData,
)
from laughtrack.scrapers.implementations.api.wix_functions_shows.extractor import (
    WixFunctionsShowsExtractor,
)
from laughtrack.scrapers.implementations.api.wix_functions_shows.transformer import (
    WixFunctionsShowEventTransformer,
)


class WixFunctionsShowsScraper(BaseScraper):
    """Scraper for public Wix/Velo shows endpoints."""

    key = "wix_functions_shows"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(WixFunctionsShowEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Scrape the endpoint URL stored in source_url."""
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[EventListContainer]:
        """Fetch the endpoint and return parsed events."""
        try:
            response = await self.fetch_json(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

        events = WixFunctionsShowsExtractor.extract_events(
            response,
            timezone_name=self.club.timezone or "UTC",
        )
        if not events:
            Logger.info(f"{self._log_prefix}: no events parsed from {url}", self.logger_context)
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} Wix/Velo show event(s)",
            self.logger_context,
        )
        return WixFunctionsShowsPageData(event_list=events)
