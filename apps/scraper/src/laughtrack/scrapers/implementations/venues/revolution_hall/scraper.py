"""
Revolution Hall scraper.

Single-page scraper for revolutionhall.com. All event data (title, date,
time, ticket URL) is available on the homepage — no pagination or
per-event detail fetching is needed.

Events are rendered as WordPress custom theme cards with Etix ticket links.
Only events with class "event-wrapper revolution-hall" are scraped (excludes
the separate Show Bar venue).
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import RevolutionHallPageData
from .extractor import RevolutionHallExtractor
from .transformer import RevolutionHallEventTransformer


class RevolutionHallScraper(BaseScraper):
    """
    Scraper for Revolution Hall (Portland, OR).

    All event data is extracted from the single homepage listing.
    """

    key = "revolution_hall"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(RevolutionHallEventTransformer(club))

    async def discover_urls(self) -> List[str]:
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[RevolutionHallPageData]:
        try:
            normalized_url = URLUtils.normalize_url(url)
            html = await self.fetch_html(normalized_url)

            if not html:
                Logger.warn(f"{self._log_prefix}: No HTML returned from {normalized_url}", self.logger_context)
                return None

            events = RevolutionHallExtractor.extract_events(html)

            if not events:
                Logger.warn(f"{self._log_prefix}: No events found on {normalized_url}", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: Extracted {len(events)} events", self.logger_context)
            return RevolutionHallPageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error in get_data: {e}", self.logger_context)
            return None
