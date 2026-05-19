"""Generic scraper for accesso ShoWare performance-list APIs."""

import re
from typing import Optional
from urllib.parse import urlencode, urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.showare import ShoWarePerformance
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ShoWarePageData
from .transformer import ShoWareTransformer

_PERFORMANCE_LIST_PATH = "/include/widgets/events/performancelist.asp"


class GenericShoWareScraper(BaseScraper):
    """Scrape accesso ShoWare performance-list widgets.

    Multipurpose theatres should configure metadata ``include_title_patterns``
    and/or ``exclude_title_patterns`` to keep the feed scoped to comedy.
    """

    key = "showare"

    def __init__(self, club: Club, **kwargs):
        source_url = URLUtils.normalize_url(club.scraping_url or "")
        base_url = _derive_base_url(source_url)
        if not base_url or "showare.com" not in urlparse(base_url).netloc:
            raise ValueError(
                "GenericShoWareScraper requires a showare.com "
                f"scraping_sources.source_url for club_id={club.id} ('{club.name}'); "
                f"got {club.scraping_url!r}"
            )

        self._base_url = base_url
        self._list_page_size = _metadata_int(club, "list_page_size", 100)

        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ShoWareTransformer(club))

    async def collect_scraping_targets(self) -> list[str]:
        params = {
            "action": "perf",
            "listPageSize": str(self._list_page_size),
            "listMaxSize": str(self._list_page_size),
            "page": "1",
        }
        return [f"{self._base_url}{_PERFORMANCE_LIST_PATH}?{urlencode(params)}"]

    async def get_data(self, url: str) -> Optional[ShoWarePageData]:
        try:
            data = await self.fetch_json(
                url,
                headers={
                    "Referer": f"{self._base_url}/default.asp",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                },
            )
            if not isinstance(data, dict):
                Logger.warn(f"{self._log_prefix}: expected ShoWare JSON object from {url}")
                return None

            raw_performances = data.get("performance") or []
            if not isinstance(raw_performances, list):
                Logger.warn(f"{self._log_prefix}: malformed ShoWare performance payload from {url}")
                return None

            events = []
            for item in raw_performances:
                if not isinstance(item, dict):
                    continue
                event = ShoWarePerformance.from_api_response(item, self._base_url)
                if event is not None:
                    events.append(event)

            events = self._dedupe_events(self._filter_events(events))
            if not events:
                Logger.info(f"{self._log_prefix}: no ShoWare performances matched configured filters")
                return None

            return ShoWarePageData(event_list=events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

    def _filter_events(self, events: list[ShoWarePerformance]) -> list[ShoWarePerformance]:
        include_patterns = self._compiled_patterns("include_title_patterns")
        exclude_patterns = self._compiled_patterns("exclude_title_patterns")

        filtered = []
        for event in events:
            title = event.title or ""
            if include_patterns and not any(pattern.search(title) for pattern in include_patterns):
                continue
            if exclude_patterns and any(pattern.search(title) for pattern in exclude_patterns):
                continue
            filtered.append(event)
        return filtered

    def _dedupe_events(self, events: list[ShoWarePerformance]) -> list[ShoWarePerformance]:
        deduped: dict[tuple[int, str], ShoWarePerformance] = {}
        for event in events:
            key = (event.event_id, event.performance_datetime)
            existing = deduped.get(key)
            if existing is None or _price_sort_value(event) < _price_sort_value(existing):
                deduped[key] = event
        return list(deduped.values())

    def _compiled_patterns(self, metadata_key: str) -> list[re.Pattern]:
        raw = (self.club.source_metadata or {}).get(metadata_key)
        if not raw:
            return []
        if isinstance(raw, str):
            values = [raw]
        elif isinstance(raw, list):
            values = [str(value) for value in raw if str(value).strip()]
        else:
            return []
        return [re.compile(value, re.IGNORECASE) for value in values]


def _derive_base_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _metadata_int(club: Club, key: str, default: int) -> int:
    raw = club.metadata_value(key)
    try:
        value = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _price_sort_value(event: ShoWarePerformance) -> float:
    return event.min_price if event.min_price is not None else float("inf")
