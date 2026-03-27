"""
The Annoyance Theatre Chicago scraper.

The Annoyance Theatre (851 W. Belmont Ave, Chicago, IL) uses ThunderTix for
ticketing.  Upcoming shows are available via the ThunderTix calendar API:

  GET https://theannoyance.thundertix.com/reports/calendar?week=0&start={ts}&end={ts+7d}

The API returns a JSON array of performance objects, one per show.  A single
request covers one 7-day window; to collect 12 weeks of upcoming shows the
scraper generates 12 weekly URLs starting from the current Sunday.

Filtering rules:
- Skip events whose title starts with "CLASS:" or "TRAINING CENTER:".
- Skip events where publicly_available is False.

Pipeline:
  1. collect_scraping_targets() → 12 weekly ThunderTix API URLs
  2. get_data(url)              → fetch JSON, filter, return AnnoyancePageData
  3. transformation_pipeline    → AnnoyancePerformance.to_show() → Show objects
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.annoyance import AnnoyancePerformance
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import AnnoyancePageData
from .transformer import AnnoyanceEventTransformer

_BASE_URL = "https://theannoyance.thundertix.com"
_CALENDAR_PATH = "/reports/calendar"

_TITLE_SKIP_PREFIXES = ("CLASS:", "TRAINING CENTER:")

_WEEKS_AHEAD = 12
_WEEK_SECONDS = 7 * 86400


def _current_week_start_ts() -> int:
    """Return the Unix timestamp (UTC) for the start of the current Sunday (midnight UTC)."""
    now = datetime.now(tz=timezone.utc)
    # isoweekday: Mon=1 … Sun=7; days since last Sunday = isoweekday % 7
    days_since_sunday = now.isoweekday() % 7
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_sunday)
    return int(week_start.timestamp())


class AnnoyanceTheatreScraper(BaseScraper):
    """Scraper for The Annoyance Theatre Chicago via ThunderTix calendar API."""

    key = "annoyance"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(AnnoyanceEventTransformer(club))

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
            f"Annoyance Theatre: generated {len(urls)} weekly API URLs",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[AnnoyancePageData]:
        """
        Fetch one week of performances from the ThunderTix calendar API.

        Args:
            url: ThunderTix calendar API URL for a single 7-day window.

        Returns:
            AnnoyancePageData with filtered performances, or None if none found.
        """
        try:
            response = await self.fetch_json(url)
            if response is None:
                Logger.info(
                    f"Annoyance Theatre: empty response from API ({url})",
                    self.logger_context,
                )
                return None

            if not isinstance(response, list):
                Logger.warn(
                    f"Annoyance Theatre: unexpected API response shape (not a list) at {url}",
                    self.logger_context,
                )
                return None

            performances: List[AnnoyancePerformance] = []
            for item in response:
                if not isinstance(item, dict):
                    continue

                # Skip non-public events
                if not item.get("publicly_available", True):
                    continue

                title = item.get("title") or ""
                if any(title.startswith(prefix) for prefix in _TITLE_SKIP_PREFIXES):
                    continue

                performances.append(AnnoyancePerformance.from_api_response(item, _BASE_URL))

            if not response:
                Logger.info(
                    f"Annoyance Theatre: no shows scheduled for this window ({url})",
                    self.logger_context,
                )
                return None

            if not performances:
                Logger.info(
                    f"Annoyance Theatre: no public performances found for window ({url})",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"Annoyance Theatre: extracted {len(performances)} performance(s) from {url}",
                self.logger_context,
            )
            return AnnoyancePageData(event_list=performances)

        except Exception as e:
            Logger.error(f"Annoyance Theatre: get_data failed for {url}: {e}", self.logger_context)
            return None
