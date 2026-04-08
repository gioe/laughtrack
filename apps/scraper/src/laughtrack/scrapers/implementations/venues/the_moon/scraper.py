"""
The Moon scraper (Tallahassee, FL).

The Moon (1105 E Lafayette St, Tallahassee, FL) lists its upcoming shows
via a WordPress page powered by the rhp-events plugin.  Tickets are sold
through eTix.

Pipeline:
  1. collect_scraping_targets() — return the single events listing page URL.
  2. get_data(url)              — fetch the listing page and extract events.
  3. transformation_pipeline    — TheMoonEvent.to_show() -> Show.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import TheMoonPageData
from .extractor import TheMoonExtractor
from .transformer import TheMoonEventTransformer


class TheMoonScraper(BaseScraper):
    """Scraper for The Moon (Tallahassee, FL)."""

    key = "the_moon"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            TheMoonEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Return the single events listing page URL."""
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[TheMoonPageData]:
        """
        Fetch the listing page and extract all event cards.

        Args:
            url: The listing page URL returned by collect_scraping_targets().

        Returns:
            TheMoonPageData with extracted events, or None on failure.
        """
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = TheMoonExtractor.extract_events(html)
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
            return TheMoonPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
