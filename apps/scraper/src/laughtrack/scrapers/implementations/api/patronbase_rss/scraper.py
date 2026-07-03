"""Generic scraper for PatronBase productions RSS feeds."""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.patronbase_rss.data import (
    PatronBaseRssPageData,
)
from laughtrack.scrapers.implementations.api.patronbase_rss.extractor import (
    PatronBaseRssExtractor,
)
from laughtrack.scrapers.implementations.api.patronbase_rss.transformer import (
    PatronBaseRssEventTransformer,
)


class PatronBaseRssScraper(BaseScraper):
    """Scraper for public PatronBase productions RSS feeds."""

    key = "patronbase_rss"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(PatronBaseRssEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Scrape the RSS feed URL stored in source_url."""
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[EventListContainer]:
        """Fetch the feed and return parsed events."""
        try:
            response = await self.fetch_html(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

        events = PatronBaseRssExtractor.extract_events(
            response,
            timezone_name=self.club.timezone or "UTC",
        )
        if not events:
            Logger.info(f"{self._log_prefix}: no events parsed from {url}", self.logger_context)
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} PatronBase RSS event(s)",
            self.logger_context,
        )
        return PatronBaseRssPageData(event_list=events)
