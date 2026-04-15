"""
Off Cabot Comedy and Events scraper (Beverly, MA).

Two-phase scraper for thecabot.org/offcabot/:
1. collect_scraping_targets() — fetch the listing page and discover event
   detail page URLs from div.event_item cards.
2. get_data(url) — fetch each event detail page and extract show rows
   with date, time, price, and ticket URL (Etix or native booking).

Multi-date events produce one Show per date (each show_row is separate).
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import OffCabotPageData
from .extractor import OffCabotExtractor
from .transformer import OffCabotEventTransformer


class OffCabotScraper(BaseScraper):
    """
    Scraper for Off Cabot Comedy and Events (Beverly, MA).

    Discovers event pages from the listing at /offcabot/, then fetches
    each detail page for full show data including Etix ticket URLs.
    """

    key = "off_cabot"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            OffCabotEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Fetch the listing page and return individual event page URLs."""
        listing_url = URLUtils.normalize_url(self.club.scraping_url)
        try:
            html = await self.fetch_html(listing_url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for listing page {listing_url}",
                    self.logger_context,
                )
                return []

            urls = OffCabotExtractor.extract_event_page_urls(html, listing_url)
            Logger.info(
                f"{self._log_prefix}: discovered {len(urls)} event pages from listing",
                self.logger_context,
            )
            return urls

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: failed to discover event pages: {e}",
                self.logger_context,
            )
            return []

    async def get_data(self, url: str) -> Optional[OffCabotPageData]:
        """
        Fetch an event detail page and extract show rows.

        Each show_row becomes an OffCabotEvent. Multi-date events
        produce multiple events from a single detail page.
        """
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = OffCabotExtractor.extract_events_from_detail(html, url)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no show rows found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} shows from {url}",
                self.logger_context,
            )
            return OffCabotPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
