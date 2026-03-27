"""
Generic Squarespace venue scraper.

Venues whose show calendar is powered by Squarespace publish event data via:
  GET {domain}/api/open/GetItemsByMonth?month=MM-YYYY&collectionId={id}

The response is a JSON array at the root level (not a dict). The scraping_url
stored in the clubs DB must be the full GetItemsByMonth endpoint including the
collectionId query parameter, e.g.:
  https://thedentheatre.com/api/open/GetItemsByMonth?collectionId=64bc3c406b6d3d1edd3c84db

The scraper fetches the current month and the next two months to capture all
upcoming shows.

Currently used by: The Den Theatre Chicago (IL), The Elysian Theater (CA).
A new Squarespace venue can be onboarded with only a DB row — no Python changes.
"""

from datetime import date
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import SquarespacePageData
from .extractor import SquarespaceExtractor
from .transformer import SquarespaceEventTransformer


class SquarespaceScraper(BaseScraper):
    """
    Generic Squarespace scraper — reads club.scraping_url for the API endpoint.

    Fetches events for the current month and the next two months.
    """

    key = "squarespace"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SquarespaceEventTransformer(club))

        parsed = urlparse(club.scraping_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
        qs = parse_qs(parsed.query)
        self.collection_id = (qs.get("collectionId") or [""])[0]

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return GetItemsByMonth URLs for the current month and next two months."""
        today = date.today()
        targets = []
        for i in range(3):
            month = (today.month + i - 1) % 12 + 1
            year = today.year + (today.month + i - 1) // 12
            month_str = f"{month:02d}-{year}"
            url = (
                f"{self.base_domain}/api/open/GetItemsByMonth"
                f"?month={month_str}&collectionId={self.collection_id}"
            )
            targets.append(url)
        return targets

    async def get_data(self, url: str) -> Optional[SquarespacePageData]:
        """
        Fetch events from the Squarespace GetItemsByMonth API.

        The API returns a JSON array at the root level (not a dict), so
        response is None means a network failure; response == [] means no shows
        scheduled for that month.
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            response = await self.fetch_json(url)
            if response is None:
                Logger.info(
                    f"SquarespaceScraper: empty response from {url}",
                    self.logger_context,
                )
                return None
            if not response:
                Logger.info(
                    f"SquarespaceScraper: no shows scheduled for {url}",
                    self.logger_context,
                )
                return None

            events = SquarespaceExtractor.extract_events(response, self.base_domain)
            if not events:
                Logger.info(
                    f"SquarespaceScraper: no events extracted from {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"SquarespaceScraper: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return SquarespacePageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"SquarespaceScraper: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None
