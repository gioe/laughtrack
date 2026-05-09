"""Configurable scraper for venues using the ThunderTix weekly calendar API."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Generic, List, Optional, Sequence, TypeVar

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper

_CALENDAR_PATH = "/reports/calendar"
_DEFAULT_WEEKS_AHEAD = 12
_WEEK_SECONDS = 7 * 86400

PerformanceT = TypeVar("PerformanceT", bound=ShowConvertible)
PageDataT = TypeVar("PageDataT", bound=EventListContainer)


def current_week_start_ts() -> int:
    """Return the Unix timestamp for the start of the current Sunday at midnight UTC."""
    now = datetime.now(tz=timezone.utc)
    days_since_sunday = now.isoweekday() % 7
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_sunday)
    return int(week_start.timestamp())


@dataclass(frozen=True)
class ThunderTixCalendarConfig(Generic[PerformanceT, PageDataT]):
    """Venue-specific settings for the ThunderTix weekly calendar API."""

    base_url: str
    event_factory: Callable[[dict, str], PerformanceT]
    page_data_factory: Callable[[List[PerformanceT]], PageDataT]
    title_skip_prefixes: Sequence[str] = field(default_factory=tuple)
    weeks_ahead: int = _DEFAULT_WEEKS_AHEAD
    calendar_path: str = _CALENDAR_PATH
    current_week_start_ts: Callable[[], int] = current_week_start_ts


class ThunderTixCalendarScraper(BaseScraper, Generic[PerformanceT, PageDataT]):
    """Base scraper for ThunderTix calendar endpoints configured per venue."""

    thundertix_config: ThunderTixCalendarConfig[PerformanceT, PageDataT]

    async def collect_scraping_targets(self) -> List[str]:
        config = self.thundertix_config
        week_start_ts = config.current_week_start_ts()
        urls = []
        for i in range(config.weeks_ahead):
            start = week_start_ts + i * _WEEK_SECONDS
            end = start + _WEEK_SECONDS
            urls.append(f"{config.base_url}{config.calendar_path}?week=0&start={start}&end={end}")

        Logger.info(
            f"{self._log_prefix}: generated {len(urls)} weekly API URLs",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[PageDataT]:
        config = self.thundertix_config
        try:
            response = await self.fetch_json_list(url)
            if response is None:
                Logger.info(
                    f"{self._log_prefix}: empty response from API ({url})",
                    self.logger_context,
                )
                return None

            performances: List[PerformanceT] = []
            for item in response:
                if not isinstance(item, dict):
                    continue

                if not item.get("publicly_available", True):
                    continue

                title = item.get("title") or ""
                if any(title.startswith(prefix) for prefix in config.title_skip_prefixes):
                    continue

                performances.append(config.event_factory(item, config.base_url))

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
            return config.page_data_factory(performances)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None
