"""Generic scraper for Timely (events.timely.fun / time.ly) calendars.

Configuration (scraping_sources.metadata):
    - timely_calendar_id (required): numeric Timely calendar id.
    - timely_api_key (optional): override for Timely's public browser API key.

The club/source URL should be the public Timely calendar URL, for example:
https://events.timely.fun/fwq8raf8/agenda
"""

from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import TimelyPageData
from .extractor import TimelyExtractor
from .transformer import TimelyTransformer

_API_BASE = "https://events.timely.fun/api"
_DEFAULT_API_KEY = "c6e5e0363b5925b28552de8805464c66f25ba0ce"
_PER_PAGE = 100
_MAX_PAGES = 20


class TimelyScraper(BaseScraper):
    """Scraper for venues using Timely's public calendar API."""

    key = "timely"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TimelyTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        calendar_id = self._calendar_id()
        if not calendar_id:
            Logger.warn(
                f"{self._log_prefix}: missing metadata.timely_calendar_id",
                self.logger_context,
            )
            return []

        return [self._events_url(calendar_id=calendar_id, page=1)]

    async def get_data(self, url: ScrapingTarget) -> Optional[TimelyPageData]:
        headers = self._headers()
        all_events = []
        current_url = str(url)

        for page in range(1, _MAX_PAGES + 1):
            response = await self.fetch_json(current_url, headers=headers)
            if not response:
                break

            events = TimelyExtractor.extract_events(
                response,
                calendar_url=self._calendar_url(),
            )
            all_events.extend(events)

            Logger.debug(
                f"{self._log_prefix}: page {page}, {len(events)} Timely event(s)",
                self.logger_context,
            )

            if not TimelyExtractor.has_next_page(response):
                break

            calendar_id = self._calendar_id()
            if not calendar_id:
                break
            current_url = self._events_url(calendar_id=calendar_id, page=page + 1)
        else:
            Logger.warn(
                f"{self._log_prefix}: reached MAX_PAGES ({_MAX_PAGES}), stopping early",
                self.logger_context,
            )

        if not all_events:
            self._warn_empty_extraction(str(url), subject="Timely events")
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(all_events)} Timely event(s)",
            self.logger_context,
        )
        return TimelyPageData(event_list=all_events)

    def _calendar_id(self) -> Optional[str]:
        value = (self.club.source_metadata or {}).get("timely_calendar_id")
        if value is None:
            return None
        value = str(value).strip()
        return value if value.isdigit() else None

    def _calendar_url(self) -> str:
        return (self.club.scraping_url or "").rstrip("/")

    def _events_url(self, calendar_id: str, page: int) -> str:
        timezone = self.club.timezone or "America/New_York"
        start_date_utc = self._local_midnight_timestamp(timezone)
        params = {
            "group_by_date": "1",
            "timezone": timezone,
            "view": "agenda",
            "start_date_utc": str(start_date_utc),
            "per_page": str(_PER_PAGE),
            "page": str(page),
        }
        return f"{_API_BASE}/calendars/{calendar_id}/events?{urlencode(params)}"

    def _headers(self) -> dict[str, str]:
        api_key = str((self.club.source_metadata or {}).get("timely_api_key") or _DEFAULT_API_KEY)
        return {
            "Accept": "application/json, text/plain, */*",
            "x-api-key": api_key,
            "Referer": self._calendar_url(),
        }

    @staticmethod
    def _local_midnight_timestamp(timezone: str) -> int:
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("America/New_York")
        now = datetime.now(tz)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(midnight.timestamp())

