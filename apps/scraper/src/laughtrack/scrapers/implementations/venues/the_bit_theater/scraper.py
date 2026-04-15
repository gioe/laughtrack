"""
The Bit Theater scraper (Aurora, IL).

The Bit Theater is an improv/comedy theater running on Odoo CMS at
bitimprov.org. All upcoming events are listed at:

  https://www.bitimprov.org/event

with pagination at /event/page/2, /event/page/3, etc.

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single entry point)
  2. get_data(url):
       a. Fetch listing pages (following pagination)
       b. Parse article cards — filter to comedy-relevant categories
       c. Fetch each event detail page to extract ticket price
  3. transformation_pipeline → BitTheaterEvent.to_show() → Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.the_bit_theater import BitTheaterEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import BitTheaterPageData
from .extractor import BitTheaterExtractor
from .transformer import BitTheaterEventTransformer

_MAX_PAGES = 5  # Safety limit on pagination


class BitTheaterScraper(BaseScraper):
    """Scraper for The Bit Theater (Aurora, IL) via Odoo CMS."""

    key = "the_bit_theater"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            BitTheaterEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[BitTheaterPageData]:
        """
        Fetch paginated event listing pages, filter to comedy events,
        and enrich each with price from the detail page.

        Args:
            url: The events listing URL (from club.scraping_url).

        Returns:
            BitTheaterPageData with extracted events, or None on failure.
        """
        try:
            all_events: List[BitTheaterEvent] = []
            current_url: Optional[str] = url
            page = 0

            # Fetch listing pages with pagination
            while current_url and page < _MAX_PAGES:
                page += 1
                html = await self.fetch_html(current_url)
                if not html:
                    Logger.warn(
                        f"{self._log_prefix}: empty response for {current_url}",
                        self.logger_context,
                    )
                    break

                events, next_url = BitTheaterExtractor.extract_listing_events(html)
                all_events.extend(events)

                Logger.info(
                    f"{self._log_prefix}: page {page} — {len(events)} comedy events",
                    self.logger_context,
                )
                current_url = next_url

            if not all_events:
                Logger.info(
                    f"{self._log_prefix}: no comedy events found across {page} page(s)",
                    self.logger_context,
                )
                return None

            # Fetch detail pages for price enrichment
            for event in all_events:
                try:
                    detail_html = await self.fetch_html(event.event_url)
                    if detail_html:
                        price = BitTheaterExtractor.extract_detail_price(detail_html)
                        if price is not None:
                            event.price = price
                except Exception as e:
                    Logger.warn(
                        f"{self._log_prefix}: failed to fetch detail for {event.event_url}: {e}",
                        self.logger_context,
                    )

            Logger.info(
                f"{self._log_prefix}: extracted {len(all_events)} comedy events total",
                self.logger_context,
            )
            return BitTheaterPageData(event_list=all_events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
