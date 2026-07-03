"""Generic scraper for FullCalendar-style JSON feeds."""

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.fullcalendar_json.data import (
    FullCalendarJsonPageData,
)
from laughtrack.scrapers.implementations.api.fullcalendar_json.extractor import (
    FullCalendarJsonExtractor,
)
from laughtrack.scrapers.implementations.api.fullcalendar_json.transformer import (
    FullCalendarJsonEventTransformer,
)


class FullCalendarJsonScraper(BaseScraper):
    """Scraper for public FullCalendar JSON feeds."""

    key = "fullcalendar_json"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.base_domain = self._base_domain(club.scraping_url)
        self.include_title_res = self.compile_title_patterns("include_title_patterns")
        self.exclude_title_res = self.compile_title_patterns("exclude_title_patterns")
        self.transformation_pipeline.register_transformer(FullCalendarJsonEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Scrape the feed URL stored in source_url."""
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[EventListContainer]:
        """Fetch the feed and return parsed events."""
        try:
            response = await self.fetch_json(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

        events = FullCalendarJsonExtractor.extract_events(
            response,
            self.base_domain,
            timezone_name=self.club.timezone or "UTC",
            include_title_res=self.include_title_res,
            exclude_title_res=self.exclude_title_res,
        )
        if not events:
            Logger.info(f"{self._log_prefix}: no events parsed from {url}", self.logger_context)
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} FullCalendar JSON event(s)",
            self.logger_context,
        )
        return FullCalendarJsonPageData(event_list=events)

    @staticmethod
    def _base_domain(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else url
