"""
Squarespace scraper implementation (generic, venue-agnostic).

Venues on Squarespace serve event data from:
  /api/open/GetItemsByMonth?month=MM-YYYY&collectionId=<id>

The collectionId and base domain are encoded in club.scraping_url:
  https://<domain>/api/open/GetItemsByMonth?collectionId=<id>

Pipeline:
  1. collect_scraping_targets() → returns month API URLs for current + next N months
  2. get_data(url)              → fetches the JSON array, extracts ElysianEvents
  3. transformation_pipeline    → ElysianEvent.to_show() → Show objects
"""

from datetime import date
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from dateutil.relativedelta import relativedelta

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import ElysianPageData
from .extractor import ElysianEventExtractor
from .transformer import ElysianEventTransformer

_MONTHS_AHEAD = 3


class ElysianTheaterScraper(BaseScraper):
    """Generic Squarespace GetItemsByMonth scraper. Reads collectionId from club.scraping_url."""

    key = "squarespace"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ElysianEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Generate month API URLs for the current month through _MONTHS_AHEAD months ahead.

        Expects club.scraping_url to be the full GetItemsByMonth URL including collectionId,
        e.g. https://<domain>/api/open/GetItemsByMonth?collectionId=<id>

        Returns URLs of the form:
          {base_url_without_qs}?month=MM-YYYY&collectionId=<id>
        """
        scraping_url = self.club.scraping_url or ""
        parsed = urlparse(scraping_url)
        qs = parse_qs(parsed.query)
        collection_id = (qs.get("collectionId") or [""])[0]
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        today = date.today()
        urls = []
        for offset in range(_MONTHS_AHEAD + 1):
            target_month = today + relativedelta(months=offset)
            month_str = target_month.strftime("%m-%Y")
            url = f"{base_url}?month={month_str}&collectionId={collection_id}"
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
                Logger.info(f"SquarespaceScraper: no response from {url}", self.logger_context)
                return None

            # The API returns a JSON array; fetch_json returns whatever response.json() yields
            api_list = response if isinstance(response, list) else []

            events = ElysianEventExtractor.extract_events(api_list)

            if not events:
                Logger.info(f"SquarespaceScraper: no events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"SquarespaceScraper: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return ElysianPageData(event_list=events)

        except Exception as e:
            Logger.error(f"SquarespaceScraper: error fetching events from {url}: {e}", self.logger_context)
            return None
