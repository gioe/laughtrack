"""
The Comedy Store scraper implementation.

The Comedy Store (8433 W Sunset Blvd, West Hollywood, CA) lists shows on a
day-by-day HTML calendar at thecomedystore.com/calendar/YYYY-MM-DD.  Tickets
are sold through ShowClix (venue 30111).

Pipeline:
  1. collect_scraping_targets() → one URL per day for the next SCRAPE_WINDOW_DAYS days
  2. get_data(url)              → fetch daily calendar HTML → extract ComedyStoreEvents
  3. transformation_pipeline   → ComedyStoreEvent.to_show() → Show objects
"""

from datetime import date, timedelta
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyStorePageData
from .extractor import ComedyStoreEventExtractor
from .transformer import ComedyStoreEventTransformer

# Number of days ahead to scrape (inclusive of today)
_SCRAPE_WINDOW_DAYS = 30


class ComedyStoreScraper(BaseScraper):
    """Scraper for The Comedy Store (West Hollywood, CA)."""

    key = "comedy_store"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ComedyStoreEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Return one calendar URL per day for the next _SCRAPE_WINDOW_DAYS days."""
        today = date.today()
        targets = [
            f"https://thecomedystore.com/calendar/{(today + timedelta(days=i)).strftime('%Y-%m-%d')}"
            for i in range(_SCRAPE_WINDOW_DAYS)
        ]
        Logger.info(
            f"Comedy Store: generated {len(targets)} daily calendar URLs "
            f"({today} – {today + timedelta(days=_SCRAPE_WINDOW_DAYS - 1)})",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[ComedyStorePageData]:
        """Fetch a single calendar day page and extract all show events."""
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(f"Comedy Store: empty response from {url}", self.logger_context)
                return None

            events = ComedyStoreEventExtractor.extract_shows(html)
            if not events:
                # Days with no shows are normal — return None to skip silently
                return None

            Logger.info(
                f"Comedy Store: extracted {len(events)} show(s) from {url}",
                self.logger_context,
            )
            return ComedyStorePageData(event_list=events)

        except Exception as e:
            Logger.error(f"Comedy Store: error scraping {url}: {e}", self.logger_context)
            return None
