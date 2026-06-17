"""Generic EventON comedy scraper (WordPress admin-ajax loader).

EventON is a popular WordPress events-calendar plugin (custom post type
``ajde_events``). Its REST endpoint exposes event posts but not their start
dates (EventON keeps dates in unexposed post meta), so the scrapable seam is the
frontend calendar loader at ``/wp-admin/admin-ajax.php`` (action
``eventon_init_load``), which returns a JSON list of upcoming events with unix
start times. Per-event permalinks and taxonomy terms are then joined from the WP
REST API, and comedy filtering uses the ``event_type`` taxonomy.

Per-venue configuration is the WordPress site root, read from the club's
``scraping_url`` (e.g. ``https://jillysmusicroom.com``). Optional
``scraping_sources.metadata`` overrides: ``cal_id`` (default ``MAIN``) and
``event_type_filter`` (comma-separated term names; when set, e.g. ``comedy``,
only events tagged with the matching ``event_type`` term are kept — for venues
that host comedy alongside other programming).

Pipeline:
    1. collect_scraping_targets(): return the WordPress site root.
    2. get_data(root): POST the loader for upcoming events, join permalinks +
       event_type terms from the REST API, optionally filter to comedy, and wrap
       as EventONPageData.
    3. transformation_pipeline: EventONEvent.to_show() -> Show objects.
"""

import json
from typing import List, Optional, Set
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import EventONPageData
from .extractor import (
    build_loader_body,
    build_rest_meta,
    discover_term_ids,
    extract_events,
    parse_loader_events,
)
from .transformer import EventONEventTransformer

_DEFAULT_CAL_ID = "MAIN"
_REST_INCLUDE_CHUNK = 100  # WP REST per_page cap


class EventONScraper(BaseScraper):
    """Comedy scraper for venues on the EventON WordPress calendar plugin."""

    key = "eventon"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(EventONEventTransformer(club))

    def _site_root(self) -> Optional[str]:
        """Origin (scheme://host) derived from the club's scraping_url."""
        raw = self.club.scraping_url
        if not raw:
            return None
        parsed = urlparse(URLUtils.normalize_url(raw))
        if not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        root = self._site_root()
        if not root:
            Logger.warn(
                f"{self._log_prefix}: Club has no scraping_url configured",
                self.logger_context,
            )
            return []
        return [root]

    async def get_data(self, target: ScrapingTarget) -> Optional[EventONPageData]:
        root = str(target).rstrip("/")
        cal_id = self.club.metadata_value("cal_id") or _DEFAULT_CAL_ID

        # 1. Loader POST -> upcoming events (id, title, start_unix).
        body = build_loader_body(cal_id=cal_id)
        try:
            text = await self.post_form(
                f"{root}/wp-admin/admin-ajax.php",
                body,
                headers={"referer": f"{root}/events/"},
            )
            loader_json = json.loads(text)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: EventON loader failed for {root}: {e}",
                self.logger_context,
            )
            return None

        loader_events = parse_loader_events(loader_json, cal_id=cal_id)
        if not loader_events:
            Logger.warn(
                f"{self._log_prefix}: EventON loader returned no upcoming events for {root}",
                self.logger_context,
            )
            return None

        event_ids = [int(e["event_id"]) for e in loader_events if e.get("event_id")]

        # 2. REST join -> permalink + event_type terms for each event post.
        rest_items = await self._fetch_rest_items(root, event_ids)
        rest_meta = build_rest_meta(rest_items)

        # 3. Optional comedy filter via the event_type taxonomy.
        comedy_term_ids = await self._resolve_filter_term_ids(root)

        events = extract_events(loader_events, rest_meta, comedy_term_ids=comedy_term_ids)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: No EventON events survived join/filter for {root}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: Extracted {len(events)} EventON event(s) from {root}",
            self.logger_context,
        )
        return EventONPageData(event_list=events)

    async def _fetch_rest_items(self, root: str, event_ids: List[int]) -> List[dict]:
        """Fetch ajde_events REST items (id, link, event_type) for *event_ids*."""
        items: List[dict] = []
        for start in range(0, len(event_ids), _REST_INCLUDE_CHUNK):
            chunk = event_ids[start : start + _REST_INCLUDE_CHUNK]
            include = ",".join(str(i) for i in chunk)
            url = (
                f"{root}/wp-json/wp/v2/ajde_events"
                f"?include={include}&per_page={_REST_INCLUDE_CHUNK}&_fields=id,link,event_type"
            )
            page = await self.fetch_json(url)
            if isinstance(page, list):
                items.extend(page)
        return items

    async def _resolve_filter_term_ids(self, root: str) -> Optional[Set[int]]:
        """Resolve ``event_type`` term ids for the configured comedy filter.

        Returns None when no filter is configured (import everything).
        """
        raw = self.club.metadata_value("event_type_filter")
        if not raw:
            return None
        names = tuple(n.strip() for n in raw.split(",") if n.strip())
        if not names:
            return None

        terms = await self.fetch_json(
            f"{root}/wp-json/wp/v2/event_type?per_page=100&_fields=id,name,slug"
        )
        if not isinstance(terms, list):
            Logger.warn(
                f"{self._log_prefix}: event_type taxonomy unavailable at {root}; "
                f"cannot apply '{raw}' filter",
                self.logger_context,
            )
            return None

        term_ids = discover_term_ids(terms, target_names=names)
        if not term_ids:
            Logger.warn(
                f"{self._log_prefix}: No event_type term matched {names} at {root}",
                self.logger_context,
            )
        return term_ids
