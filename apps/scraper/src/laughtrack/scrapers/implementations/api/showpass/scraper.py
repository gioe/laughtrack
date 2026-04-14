"""
Generic Showpass scraper for venues that use Showpass for ticketing.

Any venue whose calendar is powered by Showpass can be onboarded with only a
DB row (scraper='showpass', scraping_url=<Showpass calendar API base URL>) —
no Python changes needed.

The scraping_url must be the Showpass public calendar API base for the venue:

  https://www.showpass.com/api/public/venues/{slug}/calendar/

The scraper extracts the venue slug from the URL path and generates 3 monthly
API requests to collect upcoming shows.

Pipeline:
  1. collect_scraping_targets() -> 3 monthly Showpass API URLs
  2. get_data(url)              -> fetch JSON, filter active, return ShowpassPageData
  3. transformation_pipeline    -> ShowpassEvent.to_show() -> Show objects
"""

import re
from datetime import datetime, timezone
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.showpass import ShowpassEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ShowpassPageData
from .transformer import ShowpassEventTransformer

_MONTHS_AHEAD = 3
_SLUG_RE = re.compile(r"/venues/([^/]+)/calendar/?")


class ShowpassScraper(BaseScraper):
    """Generic scraper for venues that use Showpass for ticketing.

    A new venue can be onboarded by inserting a DB row with scraper='showpass'
    and scraping_url set to the Showpass calendar API base URL — no code
    changes required.
    """

    key = "showpass"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ShowpassEventTransformer(club))
        self._venue_slug = self._extract_slug(club.scraping_url)

    @staticmethod
    def _extract_slug(scraping_url: str) -> str:
        """Extract the venue slug from the Showpass calendar API URL."""
        m = _SLUG_RE.search(scraping_url)
        if not m:
            raise ValueError(
                f"Cannot extract Showpass venue slug from scraping_url: {scraping_url}. "
                "Expected format: https://www.showpass.com/api/public/venues/{slug}/calendar/"
            )
        return m.group(1)

    async def collect_scraping_targets(self) -> List[str]:
        """Generate monthly Showpass calendar API URLs starting from today."""
        now = datetime.now(tz=timezone.utc)
        base = f"https://www.showpass.com/api/public/venues/{self._venue_slug}/calendar/"
        urls = []
        for i in range(_MONTHS_AHEAD):
            month_start = (now + relativedelta(months=i)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            month_end = month_start + relativedelta(months=1)
            url = (
                f"{base}"
                f"?only_parents=true"
                f"&page_size=100"
                f"&ends_on__gte={month_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')}"
                f"&starts_on__lt={month_end.strftime('%Y-%m-%dT%H:%M:%S.000Z')}"
                f"&slug={self._venue_slug}"
                f"&version=1"
            )
            urls.append(url)
        Logger.info(
            f"{self._log_prefix}: generated {len(urls)} monthly API URLs",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[ShowpassPageData]:
        """Fetch one month of events from the Showpass calendar API."""
        try:
            response = await self.fetch_json(url)
            if response is None:
                Logger.info(
                    f"{self._log_prefix}: empty response from API ({url})",
                    self.logger_context,
                )
                return None

            results = response.get("results", [])
            if not results:
                Logger.info(
                    f"{self._log_prefix}: no events in this window ({url})",
                    self.logger_context,
                )
                return None

            events: List[ShowpassEvent] = []
            for item in results:
                if not isinstance(item, dict):
                    continue
                if item.get("status") != "sp_event_active":
                    continue
                events.append(ShowpassEvent.from_api_response(item))

            if not events:
                Logger.info(
                    f"{self._log_prefix}: no active events in this window ({url})",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} event(s) from {url}",
                self.logger_context,
            )
            return ShowpassPageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None
