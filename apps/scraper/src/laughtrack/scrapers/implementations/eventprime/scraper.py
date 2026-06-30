"""EventPrime platform scraper.

EventPrime is a common WordPress events plugin. Venues running it expose a
public, unauthenticated REST endpoint at
``<site>/wp-json/eventprime/v1/get_events`` that returns every event as JSON.
This generic scraper fetches that endpoint and maps each upcoming event to a
Show — no per-venue code needed.

Wiring (``scraping_sources``): set ``scraper_key='eventprime'``,
``platform='custom'``, and ``source_url`` to the full ``get_events`` endpoint
(``https://<site>/wp-json/eventprime/v1/get_events``). Optional
``metadata.comedy_filter=true`` for mixed-use venues.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone as _tz
from typing import Any, List, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.eventprime.data import EventPrimePageData
from laughtrack.scrapers.implementations.eventprime.extractor import (
    _parse_datetime,
    _string_value,
    extract_eventprime_events,
)
from laughtrack.scrapers.implementations.eventprime.transformer import (
    EventPrimeTransformer,
)
from laughtrack.scrapers.utils.comedy_filter import is_comedy_filter_enabled
from laughtrack.shared.types import ScrapingTarget

_MIDNIGHT_DETAIL_FETCH_CONCURRENCY = 5
_EVENTPRIME_META_RE = re.compile(r'"(?P<key>em_[^"]+)"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"')


class EventPrimeScraper(BaseScraper):
    """Scraper for WordPress venues running the EventPrime events plugin."""

    key = "eventprime"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(EventPrimeTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        source_url = self.club.scraping_url
        if not source_url:
            Logger.warn(
                f"{self._log_prefix}: Club has no EventPrime source_url configured "
                f"(expected the /wp-json/eventprime/v1/get_events endpoint)",
                self.logger_context,
            )
            return []
        return [URLUtils.normalize_url(source_url)]

    async def get_data(self, target: ScrapingTarget) -> Optional[EventPrimePageData]:
        try:
            payload = await self.fetch_json(str(target))
            if not payload:
                self._warn_empty_extraction(str(target), subject="payload", payload=payload)
                return None
            payload = await self._enrich_midnight_start_times(payload)

            events = extract_eventprime_events(
                payload,
                timezone=self.club.timezone,
                comedy_filter=is_comedy_filter_enabled(self.club.source_metadata),
            )
            if not events:
                count = payload.get("count") if isinstance(payload, dict) else None
                self._warn_empty_extraction(str(target), subject="events", n_items=count)
                return None
            return EventPrimePageData(events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error fetching EventPrime events from {target}: {e}",
                self.logger_context,
            )
            return None

    async def _enrich_midnight_start_times(self, payload: Any) -> Any:
        events_raw = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events_raw, list):
            return payload

        tzinfo = ZoneInfo(self.club.timezone)
        candidates = [
            (index, raw) for index, raw in enumerate(events_raw) if self._needs_midnight_detail_time(raw, tzinfo)
        ]
        if not candidates:
            return payload

        semaphore = asyncio.Semaphore(_MIDNIGHT_DETAIL_FETCH_CONCURRENCY)
        results = await asyncio.gather(
            *(self._enrich_one_midnight_event(index, raw, semaphore, tzinfo) for index, raw in candidates)
        )
        replacements = {index: enriched for index, enriched in results if enriched is not None}
        if not replacements:
            return payload

        events = [replacements.get(index, raw) for index, raw in enumerate(events_raw)]
        return {**payload, "events": events}

    def _needs_midnight_detail_time(self, raw: Any, tzinfo: ZoneInfo) -> bool:
        if not isinstance(raw, dict):
            return False
        if _string_value(raw.get("status")) not in ("", "publish"):
            return False
        if not _string_value(raw.get("permalink")):
            return False
        if _string_value(raw.get("em_all_day")) == "1":
            return False
        start_date = _parse_datetime(raw.get("start_date"), tzinfo)
        if start_date is None or start_date.astimezone(_tz.utc) < datetime.now(_tz.utc):
            return False
        return start_date.hour == 0 and start_date.minute == 0

    async def _enrich_one_midnight_event(
        self,
        index: int,
        raw: dict[str, Any],
        semaphore: asyncio.Semaphore,
        tzinfo: ZoneInfo,
    ) -> tuple[int, dict[str, Any] | None]:
        url = _string_value(raw.get("permalink"))
        try:
            async with semaphore:
                html = await self.fetch_html(url, skip_js_fallback=True)
            metadata = _extract_eventprime_metadata(html or "")
            if metadata.get("em_all_day") == "1":
                return index, None
            start_time = _parse_eventprime_time(metadata.get("em_start_time"))
            start_date = _parse_datetime(raw.get("start_date"), tzinfo)
            if start_time is None or start_date is None:
                return index, None
            enriched_start = start_date.replace(
                hour=start_time.hour,
                minute=start_time.minute,
                second=0,
                microsecond=0,
            )
            return index, {**raw, "start_date": enriched_start.isoformat()}
        except Exception as exc:
            Logger.warn(
                f"{self._log_prefix}: EventPrime detail time enrichment failed for {url}: {exc}",
                self.logger_context,
            )
            return index, None


def _extract_eventprime_metadata(html: str) -> dict[str, str]:
    return {
        match.group("key"): bytes(match.group("value"), "utf-8").decode("unicode_escape")
        for match in _EVENTPRIME_META_RE.finditer(html or "")
    }


def _parse_eventprime_time(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None
