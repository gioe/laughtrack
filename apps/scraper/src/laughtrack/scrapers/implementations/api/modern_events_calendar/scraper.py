"""Generic scraper for WordPress Modern Events Calendar sites.

Modern Events Calendar stores events as the ``mec-events`` custom post type and
exposes a WordPress REST collection at ``/wp-json/wp/v2/mec-events``. The public
REST payload does not include event datetimes on all sites, but each event detail
page renders schema.org Event JSON-LD with start/end dates and ticket offers.
This scraper uses the REST collection as the index and JSON-LD detail pages as
the canonical event source.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.data import JsonLdPageData
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.scrapers.implementations.json_ld.transformer import JsonLdTransformer

_DEFAULT_PER_PAGE = 20
_DEFAULT_MAX_PAGES = 3
_DEFAULT_MAX_DETAIL_PAGES = 60


class ModernEventsCalendarScraper(BaseScraper):
    """Scraper for Modern Events Calendar WordPress REST + JSON-LD detail pages."""

    key = "modern_events_calendar"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(JsonLdTransformer(club))

    async def get_data(self, url: str) -> Optional[JsonLdPageData]:
        """Fetch MEC REST pages, then parse JSON-LD from each event detail page."""
        event_urls = await self._collect_event_urls(url)
        if not event_urls:
            self._warn_empty_extraction(url, extra={"source": "mec-events REST"})
            return None

        events: list[JsonLdEvent] = []
        max_details = self._metadata_int("max_detail_pages", _DEFAULT_MAX_DETAIL_PAGES)
        for event_url in event_urls[:max_details]:
            html = await self._fetch_detail_html(event_url)
            if not html:
                continue
            extracted = EventExtractor.extract_events(
                html,
                same_as_override=event_url if self._set_same_as_to_detail_url() else None,
            )
            for event in extracted:
                if self._is_future_event(event):
                    events.append(event)

        if not events:
            self._warn_empty_extraction(
                url,
                extra={"detail_pages": min(len(event_urls), max_details)},
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} future MEC JSON-LD events "
            f"from {min(len(event_urls), max_details)} detail pages",
            self.logger_context,
        )
        return JsonLdPageData(event_list=events)

    async def _collect_event_urls(self, source_url: str) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        max_pages = self._metadata_int("max_pages", _DEFAULT_MAX_PAGES)
        per_page = self._metadata_int("per_page", _DEFAULT_PER_PAGE)

        for page in range(1, max_pages + 1):
            api_url = self._with_query_params(
                source_url,
                {
                    "per_page": str(per_page),
                    "page": str(page),
                    "status": "publish",
                },
            )
            payload = await self.fetch_json(api_url)
            if not payload:
                break
            if isinstance(payload, dict):
                if payload.get("code") == "rest_post_invalid_page_number":
                    break
                Logger.warn(
                    f"{self._log_prefix}: unexpected MEC REST payload type dict from {api_url}",
                    self.logger_context,
                )
                break
            if not isinstance(payload, list):
                Logger.warn(
                    f"{self._log_prefix}: unexpected MEC REST payload type "
                    f"{type(payload).__name__} from {api_url}",
                    self.logger_context,
                )
                break
            if not payload:
                break

            for raw in payload:
                if not isinstance(raw, dict):
                    continue
                event_url = str(raw.get("link") or "").strip()
                if event_url and event_url not in seen:
                    seen.add(event_url)
                    urls.append(event_url)

            if len(payload) < per_page:
                break

        Logger.info(
            f"{self._log_prefix}: collected {len(urls)} MEC detail URLs from {source_url}",
            self.logger_context,
        )
        return urls

    async def _fetch_detail_html(self, url: str) -> Optional[str]:
        if self._force_js_rendering():
            return await self._fetch_html_with_js(url)
        return await self.fetch_html(url)

    def _force_js_rendering(self) -> bool:
        return bool((self.club.source_metadata or {}).get("force_js_rendering"))

    def _set_same_as_to_detail_url(self) -> bool:
        return (self.club.source_metadata or {}).get("set_same_as_to_detail_url") is not False

    def _metadata_int(self, key: str, default: int) -> int:
        raw = (self.club.source_metadata or {}).get(key)
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _is_future_event(event: JsonLdEvent) -> bool:
        event_date = event.start_date
        now = datetime.now(event_date.tzinfo) if event_date.tzinfo else datetime.now()
        return event_date >= now

    @staticmethod
    def _with_query_params(url: str, params: dict[str, str]) -> str:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(params)
        return urlunparse(parsed._replace(query=urlencode(query)))
