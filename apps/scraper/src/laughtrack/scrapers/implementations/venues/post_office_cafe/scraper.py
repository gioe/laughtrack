"""
Post Office Cafe & Cabaret (Provincetown, MA) scraper.

Post Office Cafe & Cabaret (303 Commercial St, Provincetown, MA) uses ThunderTix
for ticketing.  Upcoming shows are available via the ThunderTix calendar API:

  GET https://postofficecafecabaret.thundertix.com/reports/calendar?week=0&start={ts}&end={ts+7d}

The API returns a JSON array of performance objects, one per show.  A single
request covers one 7-day window; to collect 12 weeks of upcoming shows the
scraper generates 12 weekly URLs starting from the current Sunday.

Filtering rules:
- Skip events where publicly_available is False.

Pipeline:
  1. collect_scraping_targets() → 12 weekly ThunderTix API URLs
  2. get_data(url)              → fetch JSON, filter, return PostOfficeCafePageData
  3. transformation_pipeline    → PostOfficeCafePerformance.to_show() → Show objects
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.post_office_cafe import PostOfficeCafePerformance
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import PostOfficeCafePageData
from .transformer import PostOfficeCafeEventTransformer

_BASE_URL = "https://postofficecafecabaret.thundertix.com"
_CALENDAR_PATH = "/reports/calendar"

_WEEKS_AHEAD = 12
_WEEK_SECONDS = 7 * 86400


def _current_week_start_ts() -> int:
    """Return the Unix timestamp (UTC) for the start of the current Sunday (midnight UTC)."""
    now = datetime.now(tz=timezone.utc)
    days_since_sunday = now.isoweekday() % 7
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_sunday)
    return int(week_start.timestamp())


class PostOfficeCafeScraper(BaseScraper):
    """Scraper for Post Office Cafe & Cabaret via ThunderTix calendar API."""

    key = "post_office_cafe"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(PostOfficeCafeEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """
        Generate 12 weekly ThunderTix calendar API URLs starting from the current Sunday.

        Returns:
            List of 12 API URLs, each covering a 7-day window.
        """
        week_start_ts = _current_week_start_ts()
        urls = []
        for i in range(_WEEKS_AHEAD):
            start = week_start_ts + i * _WEEK_SECONDS
            end = start + _WEEK_SECONDS
            url = f"{_BASE_URL}{_CALENDAR_PATH}?week=0&start={start}&end={end}"
            urls.append(url)
        Logger.info(
            f"{self._log_prefix}: generated {len(urls)} weekly API URLs",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[PostOfficeCafePageData]:
        """
        Fetch one week of performances from the ThunderTix calendar API.

        Args:
            url: ThunderTix calendar API URL for a single 7-day window.

        Returns:
            PostOfficeCafePageData with filtered performances, or None if none found.
        """
        try:
            response = await self.fetch_json_list(url)
            if response is None:
                Logger.info(
                    f"{self._log_prefix}: empty response from API ({url})",
                    self.logger_context,
                )
                return None

            performances: List[PostOfficeCafePerformance] = []
            for item in response:
                if not isinstance(item, dict):
                    continue

                # Skip non-public events
                if not item.get("publicly_available", True):
                    continue

                performances.append(PostOfficeCafePerformance.from_api_response(item, _BASE_URL))

            if not response:
                Logger.info(
                    f"{self._log_prefix}: no shows scheduled for this window ({url})",
                    self.logger_context,
                )
                return None

            if not performances:
                Logger.info(
                    f"{self._log_prefix}: no public performances found for window ({url})",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(performances)} performance(s) from {url}",
                self.logger_context,
            )
            return PostOfficeCafePageData(event_list=performances)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None
