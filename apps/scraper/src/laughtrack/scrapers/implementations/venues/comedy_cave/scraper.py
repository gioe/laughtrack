"""
Comedy Cave (Calgary, AB) scraper.

Comedy Cave (1020 8th Avenue SW, Calgary, AB) uses Showpass for ticketing.
The club's WordPress site embeds a Showpass calendar widget that fetches from
the public calendar API:

  GET https://www.showpass.com/api/public/venues/{slug}/calendar/
      ?venue__in={venue_id}&only_parents=true&page_size=100
      &ends_on__gte={start}&starts_on__lt={end}

The API returns a JSON object with a ``results`` array of event objects.  Each
request covers one calendar month; to collect ~3 months of upcoming shows the
scraper generates 3 monthly URLs starting from today.

Pipeline:
  1. collect_scraping_targets() -> 3 monthly Showpass API URLs
  2. get_data(url)              -> fetch JSON, filter active, return ComedyCavePageData
  3. transformation_pipeline    -> ShowpassEvent.to_show() -> Show objects
"""

from datetime import datetime, timezone
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.showpass import ShowpassEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyCavePageData
from .transformer import ComedyCaveEventTransformer

_SHOWPASS_API = "https://www.showpass.com/api/public/venues"
_VENUE_SLUG = "comedy-cave"
_VENUE_ID = 15525
_MONTHS_AHEAD = 3


class ComedyCaveScraper(BaseScraper):
    """Scraper for Comedy Cave via Showpass public calendar API."""

    key = "comedy_cave"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ComedyCaveEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Generate monthly Showpass calendar API URLs starting from today."""
        now = datetime.now(tz=timezone.utc)
        urls = []
        for i in range(_MONTHS_AHEAD):
            month_start = (now + relativedelta(months=i)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            month_end = month_start + relativedelta(months=1)
            url = (
                f"{_SHOWPASS_API}/{_VENUE_SLUG}/calendar/"
                f"?venue__in={_VENUE_ID}"
                f"&only_parents=true"
                f"&page_size=100"
                f"&ends_on__gte={month_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')}"
                f"&starts_on__lt={month_end.strftime('%Y-%m-%dT%H:%M:%S.000Z')}"
                f"&slug={_VENUE_SLUG}"
                f"&version=1"
            )
            urls.append(url)
        Logger.info(
            f"{self._log_prefix}: generated {len(urls)} monthly API URLs",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[ComedyCavePageData]:
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
                # Skip inactive events
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
            return ComedyCavePageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None
