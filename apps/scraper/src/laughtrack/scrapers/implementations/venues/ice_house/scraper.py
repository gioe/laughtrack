"""
Tockify scraper implementation.

Venues publishing their calendar via the Tockify embedded calendar widget
(tockify.com) store the full API URL in club.scraping_url, e.g.:

  https://tockify.com/api/ngevent?calname=theicehouse&max=200

The scraper appends a startms timestamp so only upcoming events are returned.
Each event includes a title, start timestamp (milliseconds), and a ShowClix
ticket URL in the customButtonLink field. The scraper normalizes embed URLs
(embed.showclix.com) to public URLs (www.showclix.com).

No authentication or special headers are required for the Tockify API.

Currently used by: Ice House Comedy Club (Pasadena, CA).
A second Tockify venue can be onboarded with only a DB row — no Python changes.
"""

import time
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import IceHousePageData
from .extractor import IceHouseExtractor
from .transformer import IceHouseEventTransformer


class IceHouseScraper(BaseScraper):
    """
    Generic Tockify scraper — reads club.scraping_url for the API base URL.

    Fetches upcoming events from the Tockify calendar API.
    The startms parameter is set to the current time so only upcoming events
    are returned.
    """

    key = "tockify"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(IceHouseEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the Tockify API URL with the current timestamp as startms."""
        now_ms = int(time.time() * 1000)
        return [f"{self.club.scraping_url}&startms={now_ms}"]

    async def get_data(self, url: str) -> Optional[IceHousePageData]:
        """
        Fetch events from the Tockify API and return extracted IceHouseEvents.

        Args:
            url: The Tockify API URL (from collect_scraping_targets)

        Returns:
            IceHousePageData containing events, or None if no events found
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            response = await self.fetch_json(url)
            if not response:
                Logger.info(f"{self._log_prefix}: no response from {url}", self.logger_context)
                return None

            events = IceHouseExtractor.extract_events(response)

            if not events:
                Logger.info(f"{self._log_prefix}: no events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return IceHousePageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None
