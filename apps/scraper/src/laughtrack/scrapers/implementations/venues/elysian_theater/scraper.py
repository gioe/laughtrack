"""
The Elysian Theater scraper implementation.

The Elysian Theater (1944 Riverside Drive, Los Angeles, CA) uses Squarespace
for its website. Events are fetched from:
  /api/open/GetItemsByMonth?month=MM-YYYY&collectionId=<id>

Pipeline:
  1. collect_scraping_targets() → returns month API URLs for current + next N months
  2. get_data(url)              → fetches the JSON array, extracts ElysianEvents
  3. transformation_pipeline    → ElysianEvent.to_show() → Show objects
"""

from datetime import date
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import ElysianPageData
from .extractor import ElysianEventExtractor
from .transformer import ElysianEventTransformer

_COLLECTION_ID = "613af44feffe2b7f78a46b63"
_MONTHS_AHEAD = 3


class ElysianTheaterScraper(BaseScraper):
    """Scraper for The Elysian Theater (Los Angeles, CA) via Squarespace GetItemsByMonth API."""

    key = "elysian_theater"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ElysianEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Generate month API URLs for the current month through _MONTHS_AHEAD months ahead.

        Returns URLs of the form:
          {base_url}?month=MM-YYYY&collectionId=613af44feffe2b7f78a46b63
        """
        base_url = self.club.scraping_url or "https://www.elysiantheater.com/api/open/GetItemsByMonth"
        today = date.today()
        urls = []
        for offset in range(_MONTHS_AHEAD + 1):
            target_month = today + relativedelta(months=offset)
            month_str = target_month.strftime("%m-%Y")
            url = f"{base_url}?month={month_str}&collectionId={_COLLECTION_ID}"
            urls.append(url)
        return urls

    async def get_data(self, url: str) -> Optional[ElysianPageData]:
        """
        Fetch events from The Elysian Theater Squarespace API for a single month.

        Args:
            url: The GetItemsByMonth API URL (including month and collectionId params)

        Returns:
            ElysianPageData containing ElysianEvent objects, or None if no events found
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            response = await self.fetch_json(url)
            if not response:
                Logger.info(f"ElysianTheaterScraper: no response from {url}", self.logger_context)
                return None

            # The API returns a JSON array; fetch_json returns whatever response.json() yields
            api_list = response if isinstance(response, list) else []

            events = ElysianEventExtractor.extract_events(api_list)

            if not events:
                Logger.info(f"ElysianTheaterScraper: no events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"ElysianTheaterScraper: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return ElysianPageData(event_list=events)

        except Exception as e:
            Logger.error(f"ElysianTheaterScraper: error fetching events from {url}: {e}", self.logger_context)
            return None
