"""Configurable scraper for venues using the ThunderTix weekly calendar API."""

import asyncio

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Generic, List, Optional, Sequence, Tuple, TypeVar

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.thundertix import ThunderTixPerformance
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.infrastructure.http.diagnostics import (
    ScrapeDiagnostics,
    bind_diagnostics,
    reset_diagnostics,
)
from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.base.detail_price_mixin import DetailPagePriceMixin

from .data import ThunderTixPageData
from .transformer import ThunderTixEventTransformer

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
    """Venue-specific settings for the ThunderTix weekly calendar API.

    ``event_factory`` must produce objects that, beyond ShowConvertible,
    expose a ``show_page_url: str`` and a mutable ``price: Optional[float]``
    (as ``ThunderTixPerformance`` does) — the scraper's detail-page price
    attachment reads and writes both.
    """

    base_url: str
    event_factory: Callable[[dict, str], PerformanceT]
    page_data_factory: Callable[[List[PerformanceT]], PageDataT]
    title_skip_prefixes: Sequence[str] = field(default_factory=tuple)
    weeks_ahead: int = _DEFAULT_WEEKS_AHEAD
    calendar_path: str = _CALENDAR_PATH
    current_week_start_ts: Callable[[], int] = current_week_start_ts


class ThunderTixCalendarScraper(DetailPagePriceMixin, BaseScraper, Generic[PerformanceT, PageDataT]):
    """Base scraper for ThunderTix calendar endpoints configured per venue.

    The calendar API carries no price field; each performance's price is
    attached from its event detail page's JSON-LD AggregateOffer via
    DetailPagePriceMixin.
    """

    thundertix_config: ThunderTixCalendarConfig[PerformanceT, PageDataT]

    # Leave 30 seconds of the orchestrator's 180-second limit for conversion
    # and persistence. These budgets are shared across every weekly window.
    _RUN_BUDGET_SECONDS = 150.0
    _CALENDAR_TIMEOUT_SECONDS = 20.0
    _PRICE_BUDGET_SECONDS = 60.0
    _PRICE_URL_TIMEOUT_SECONDS = 10.0
    _PRICE_CONCURRENCY = 4

    def _start_run(self):
        self._run_deadline = asyncio.get_running_loop().time() + self._RUN_BUDGET_SECONDS
        self._price_deadline = None
        self._price_semaphore = asyncio.Semaphore(self._PRICE_CONCURRENCY)
        # Separate from the mixin cache: its fetch helper evicts failures.
        self._run_price_tasks = {}
        self._price_blocked_count = 0
        self._detail_price_tasks = {}

    def _ensure_run(self):
        if not hasattr(self, "_run_deadline"):
            self._start_run()

    @staticmethod
    def _calendar_error(message, cause=None):
        error = DataError(message, "thundertix_calendar", cause)
        error.severity = ErrorSeverity.HIGH
        return error

    async def _fetch_all_raw_data(self, targets):
        self._ensure_run()
        try:
            # Includes the base scraper's rate-limit wait before get_data.
            return await asyncio.wait_for(
                super()._fetch_all_raw_data(targets),
                max(0, self._run_deadline - asyncio.get_running_loop().time()),
            )
        except asyncio.TimeoutError as exc:
            raise self._calendar_error("ThunderTix run deadline exceeded", exc) from exc
        finally:
            tasks = list(self._run_price_tasks.values())
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            known = sum(
                not task.cancelled() and task.exception() is None and task.result() is not None for task in tasks
            )
            Logger.info(
                f"{self._log_prefix}: optional prices attempted={len(tasks)}, known={known}, "
                f"unknown={len(tasks) - known}, bot_blocked={self._price_blocked_count}",
                self.logger_context,
            )

    def _detail_page_price(self, url):
        self._ensure_run()
        if url not in self._run_price_tasks:
            now = asyncio.get_running_loop().time()
            if self._price_deadline is None:
                self._price_deadline = min(self._run_deadline, now + self._PRICE_BUDGET_SECONDS)
            self._run_price_tasks[url] = asyncio.create_task(self._bounded_price(url))
        return self._run_price_tasks[url]

    async def _bounded_price(self, url):
        remaining = self._price_deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return None

        async def fetch():
            async with self._price_semaphore:
                return await asyncio.wait_for(self._fetch_detail_page_price(url), self._PRICE_URL_TIMEOUT_SECONDS)

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            # The shared deadline includes the queue; each acquired slot has its
            # own timeout including rate limiting, retries, and parsing.
            return await asyncio.wait_for(fetch(), remaining)
        except Exception as exc:
            Logger.warn(
                f"{self._log_prefix}: optional price unavailable for {url}: {type(exc).__name__}: {exc}",
                self.logger_context,
            )
            return None
        finally:
            reset_diagnostics(token)
            if diagnostics.bot_block_detected:
                self._price_blocked_count += 1
                Logger.warn(
                    f"{self._log_prefix}: optional price bot-blocked for {url}: "
                    f"status={diagnostics.http_status}, signature={diagnostics.bot_block_signature}",
                    self.logger_context,
                )

    async def collect_scraping_targets(self) -> List[str]:
        self._start_run()
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
            self._ensure_run()
            remaining = self._run_deadline - asyncio.get_running_loop().time()
            response = await asyncio.wait_for(
                self.fetch_json_list(url), min(self._CALENDAR_TIMEOUT_SECONDS, max(0, remaining))
            )
            if not isinstance(response, list):
                raise ValueError("calendar did not return an explicit list")

            performances: List[PerformanceT] = []
            for item in response:
                if not isinstance(item, dict):
                    raise ValueError("calendar contained a non-object performance")

                if not item.get("publicly_available", True):
                    continue

                title = item.get("title") or ""
                if any(title.startswith(prefix) for prefix in config.title_skip_prefixes):
                    continue

                performance = config.event_factory(item, config.base_url)
                if isinstance(performance, ThunderTixPerformance) and (
                    not performance.title.strip() or not performance.start_dt
                ):
                    raise ValueError("ThunderTix performance missing required title/start")
                resolve_start = getattr(performance, "resolve_start_datetime", None)
                if callable(resolve_start):
                    if resolve_start(self.club) is None:
                        raise ValueError("ThunderTix performance has no valid start time")
                performances.append(performance)

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

            await self._attach_detail_page_prices(performances, self._detail_price_url)

            Logger.info(
                f"{self._log_prefix}: extracted {len(performances)} performance(s) from {url}",
                self.logger_context,
            )
            return config.page_data_factory(performances)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            raise self._calendar_error(f"ThunderTix calendar failed for {url}: {e}", e) from e

    def _detail_price_url(self, performance: PerformanceT) -> Optional[str]:
        """Detail-page URL for a performance's price fetch.

        An empty truncated_url leaves show_page_url == base_url; the venue
        root has no event JSON-LD, so skip it (price stays unknown).
        """
        url = performance.show_page_url
        if not url or url == self.thundertix_config.base_url:
            return None
        return url


_CALENDAR_PATH_SUFFIX = _CALENDAR_PATH.lstrip("/")


def _parse_title_skip_prefixes(raw: Optional[str]) -> Tuple[str, ...]:
    if not raw:
        return ()
    return tuple(p.strip() for p in raw.split(",") if p.strip())


def _derive_base_url(scraping_url: str) -> str:
    url = (scraping_url or "").strip().rstrip("/")
    if url.endswith(f"/{_CALENDAR_PATH_SUFFIX}"):
        url = url[: -len(_CALENDAR_PATH_SUFFIX) - 1]
    return url


class GenericThunderTixScraper(ThunderTixCalendarScraper[ThunderTixPerformance, ThunderTixPageData]):
    """ThunderTix scraper configured per-club from ``scraping_sources``.

    Reads the venue base URL from ``scraping_sources.source_url`` (the
    venue root, e.g. ``https://theannoyance.thundertix.com``; a trailing
    ``/reports/calendar`` is tolerated and stripped). Optional
    ``title_skip_prefixes`` metadata key — comma-separated — filters out
    events whose title starts with any of the prefixes (e.g.
    ``"CLASS:,TRAINING CENTER:"`` for The Annoyance Theatre's class
    listings). ``weeks_ahead`` defaults to 12 and accepts integers from 1
    through 26; the shared run deadlines apply regardless of horizon.
    """

    key = "thundertix"

    def __init__(self, club: Club, **kwargs):
        base_url = _derive_base_url(club.scraping_url)
        if not base_url or "thundertix.com" not in base_url:
            raise ValueError(
                f"GenericThunderTixScraper requires a scraping_sources.source_url "
                f"pointing at a thundertix.com host for club_id={club.id} ('{club.name}'); "
                f"got {club.scraping_url!r}"
            )
        title_skip_prefixes = _parse_title_skip_prefixes(club.metadata_value("title_skip_prefixes"))

        raw_weeks = club.metadata_value("weeks_ahead")
        weeks_ahead = _DEFAULT_WEEKS_AHEAD
        if raw_weeks is not None:
            if not raw_weeks.isascii() or not raw_weeks.isdecimal() or not 1 <= int(raw_weeks) <= 26:
                raise ValueError("ThunderTix weeks_ahead must be an integer from 1 through 26")
            weeks_ahead = int(raw_weeks)

        self.thundertix_config = ThunderTixCalendarConfig(
            base_url=base_url,
            event_factory=ThunderTixPerformance.from_api_response,
            page_data_factory=lambda events: ThunderTixPageData(event_list=events),
            title_skip_prefixes=title_skip_prefixes,
            weeks_ahead=weeks_ahead,
        )

        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ThunderTixEventTransformer(club))
