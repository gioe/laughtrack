"""
Delirious Comedy Club scraper (FriendlySky platform).

Delirious Comedy Club (4100 Paradise Rd, Las Vegas, NV) uses the FriendlySky
ticketing platform at tickets.deliriouscomedyclub.com.

The API endpoint returns all upcoming games in a single call:

  GET /rest/events/$EKR?_branch=findByDomainNameOrHashId&_s=1

Required headers:
  - hashsiteid: e9b   (site identifier)
  - source: ONLINE
  - accept: application/json

No session cookie or auth token is needed — the headers alone are sufficient.

The response contains a ``data.games`` array with ~200+ shows. Each game has
a name field with comma-separated comedian names, date/time info, and a hashId
used to construct the ticket URL.

Pipeline:
  1. collect_scraping_targets() → single API URL
  2. get_data(url)              → fetch JSON, extract games, return DeliriousPageData
  3. transformation_pipeline    → FriendlySkyEvent.to_show() → Show objects
"""

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import DeliriousPageData
from .extractor import DeliriousExtractor
from .transformer import DeliriousEventTransformer

_API_PATH = "/rest/events/$EKR?_branch=findByDomainNameOrHashId&_s=1"

_FRIENDLYSKY_HEADERS = {
    "hashsiteid": "e9b",
    "source": "ONLINE",
    "accept": "application/json",
}


class DeliriousComedyClubScraper(BaseScraper):
    """Scraper for Delirious Comedy Club via FriendlySky API."""

    key = "delirious"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            DeliriousEventTransformer(club)
        )

    def _get_base_url(self) -> str:
        """Derive the base URL from the club's scraping_url."""
        if self.club.scraping_url:
            parsed = urlparse(self.club.scraping_url)
            return f"{parsed.scheme}://{parsed.netloc}"
        return "https://tickets.deliriouscomedyclub.com"

    async def collect_scraping_targets(self) -> List[str]:
        """Return the single FriendlySky API URL."""
        base = self._get_base_url()
        url = f"{base}{_API_PATH}"
        Logger.info(
            f"{self._log_prefix}: using API URL {url}",
            self.logger_context,
        )
        return [url]

    async def get_data(self, url: str) -> Optional[DeliriousPageData]:
        """Fetch all games from the FriendlySky events API.

        Args:
            url: FriendlySky events API URL.

        Returns:
            DeliriousPageData with extracted events, or None if no games found.
        """
        try:
            response = await self.fetch_json(url, headers=_FRIENDLYSKY_HEADERS)
            if response is None:
                Logger.info(
                    f"{self._log_prefix}: empty response from API ({url})",
                    self.logger_context,
                )
                return None

            base_url = self._get_base_url()
            events = DeliriousExtractor.extract_events(response, base_url)

            if not events:
                Logger.info(
                    f"{self._log_prefix}: no active games found ({url})",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} game(s) from API",
                self.logger_context,
            )
            return DeliriousPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: get_data failed for {url}: {e}",
                self.logger_context,
            )
            return None
