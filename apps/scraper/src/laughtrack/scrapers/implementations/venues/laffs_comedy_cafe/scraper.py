"""
Laffs Comedy Cafe scraper (Tucson, AZ).

Laffs Comedy Cafe (2900 E Broadway Blvd) is a comedy club that sells
tickets directly through their own website. All upcoming shows are
listed on a single page:

  https://www.laffstucson.com/coming-soon.html

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single page)
  2. get_data(url)              → fetch HTML, extract LaffsComedyCafeEvents
  3. transformation_pipeline    → LaffsComedyCafeEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import LaffsComedyCafePageData
from .extractor import LaffsComedyCafeExtractor
from .transformer import LaffsComedyCafeEventTransformer


class LaffsComedyCafeScraper(BaseScraper):
    """Scraper for Laffs Comedy Cafe (Tucson) via custom HTML."""

    key = "laffs_comedy_cafe"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            LaffsComedyCafeEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[LaffsComedyCafePageData]:
        """
        Fetch the coming-soon page and extract all upcoming events.

        Args:
            url: The coming-soon page URL (from club.scraping_url).

        Returns:
            LaffsComedyCafePageData with extracted events, or None on failure.
        """
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = LaffsComedyCafeExtractor.extract_events(html)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return LaffsComedyCafePageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
