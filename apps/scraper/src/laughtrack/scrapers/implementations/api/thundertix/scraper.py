"""Configurable scraper for venues using the ThunderTix weekly calendar API."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Generic, List, Optional, Sequence, Tuple, TypeVar

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.thundertix import ThunderTixPerformance
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger
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


class ThunderTixCalendarScraper(
    DetailPagePriceMixin, BaseScraper, Generic[PerformanceT, PageDataT]
):
    """Base scraper for ThunderTix calendar endpoints configured per venue.

    The calendar API carries no price field; each performance's price is
    attached from its event detail page's JSON-LD AggregateOffer via
    DetailPagePriceMixin.
    """

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

            await self._attach_detail_page_prices(performances, self._detail_price_url)

            Logger.info(
                f"{self._log_prefix}: extracted {len(performances)} performance(s) from {url}",
                self.logger_context,
            )
            return config.page_data_factory(performances)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

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


class GenericThunderTixScraper(
    ThunderTixCalendarScraper[ThunderTixPerformance, ThunderTixPageData]
):
    """ThunderTix scraper configured per-club from ``scraping_sources``.

    Reads the venue base URL from ``scraping_sources.source_url`` (the
    venue root, e.g. ``https://theannoyance.thundertix.com``; a trailing
    ``/reports/calendar`` is tolerated and stripped). Optional
    ``title_skip_prefixes`` metadata key — comma-separated — filters out
    events whose title starts with any of the prefixes (e.g.
    ``"CLASS:,TRAINING CENTER:"`` for The Annoyance Theatre's class
    listings).
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
        title_skip_prefixes = _parse_title_skip_prefixes(
            club.metadata_value("title_skip_prefixes")
        )

        self.thundertix_config = ThunderTixCalendarConfig(
            base_url=base_url,
            event_factory=ThunderTixPerformance.from_api_response,
            page_data_factory=lambda events: ThunderTixPageData(event_list=events),
            title_skip_prefixes=title_skip_prefixes,
        )

        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ThunderTixEventTransformer(club))
