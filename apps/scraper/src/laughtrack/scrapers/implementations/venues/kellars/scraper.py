"""
Kellar's: Modern Magic and Comedy Club scraper.

Kellar's (1402 State St, Erie, PA 16501) lists upcoming shows on a
WordPress site using the Starter Events Calendar plugin.  Events are
rendered as HTML cards on the /tc-events/ listing page with built-in
ticket purchasing.

Pipeline:
  1. collect_scraping_targets() — return the events listing page URL.
  2. get_data(url)              — fetch the page and extract event cards.
  3. transformation_pipeline   — KellarsEvent.to_show() → Show.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import KellarsPageData
from .extractor import KellarsExtractor
from .transformer import KellarsEventTransformer


class KellarsScraper(BaseScraper):
    """Scraper for Kellar's: Modern Magic and Comedy Club (Erie, PA)."""

    key = "kellars"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            KellarsEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Return the single events listing page URL."""
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[KellarsPageData]:
        """Fetch the listing page and extract all event cards."""
        try:
            html = await self.fetch_html(URLUtils.normalize_url(url))
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = KellarsExtractor.extract_events(html)
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
            return KellarsPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
