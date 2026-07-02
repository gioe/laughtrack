"""Aggregate Pabst Theater Group event-list scraper.

Unlike the per-venue ``pabst_axs`` scraper, this source-target scraper reads the
operator-wide event calendar and routes each event to its physical theater.
"""

import asyncio
from typing import List, Optional
from urllib.parse import urlsplit, urlunsplit

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.database.write_lock import serialized_db_call
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget
from laughtrack.scrapers.utils.comedy_filter import (
    is_comedy_filter_enabled,
    resolve_allowlist,
    resolve_min_popularity,
    select_comedy_titles,
)

from .extractor import extract_events
from .data import PabstAXSPageData

_DEFAULT_EVENTS_URL = "https://www.pabsttheatergroup.com/events"
_PAGE_SIZE = 12
_MAX_AJAX_PAGES = 80


class PabstTheaterGroupScraper(BaseScraper):
    """Operator calendar scraper for pabsttheatergroup.com/events."""

    key = "pabst_theater_group"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()
        self._comedy_filter = is_comedy_filter_enabled(self.club.source_metadata)
        self._lineup_handler = LineupHandler() if self._comedy_filter else None
        self._comedian_handler = ComedianHandler() if self._comedy_filter else None

    async def get_data(self, target: ScrapingTarget) -> Optional[PabstAXSPageData]:
        html = await self.fetch_html(target, scraper_key=self.key)
        events = extract_events(html or "")
        events = [event for event in events if event.venue_name]
        return PabstAXSPageData(event_list=events) if events else None

    async def scrape_async(self) -> List[Show]:
        events = await self._collect_events()
        if self._comedy_filter:
            events = await self._filter_comedy(events)
        if not events:
            Logger.warn(f"{self._log_prefix}: no routable Pabst Theater Group events parsed")
            return []

        loop = asyncio.get_running_loop()
        shows: List[Show] = []
        for event in events:
            venue = await self._upsert_venue(loop, event.venue_payload())
            if venue is None:
                Logger.warn(
                    f"{self._log_prefix}: could not resolve venue '{event.venue_name}' for {event.show_page_url}"
                )
                continue
            show = event.to_show(venue)
            if show is not None:
                shows.append(show)

        Logger.info(f"{self._log_prefix}: built {len(shows)} Pabst show(s) across venues")
        return shows

    async def _collect_events(self) -> List:
        page_url = self.club.scraping_url or _DEFAULT_EVENTS_URL
        try:
            html = await self.fetch_html(page_url, scraper_key=self.key)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to fetch Pabst operator page {page_url}: {e}")
            return []

        seen_urls = set()
        events = self._dedupe_routable_events(extract_events(html or ""), seen_urls)
        origin = self._origin(page_url)

        for page_index in range(1, _MAX_AJAX_PAGES + 1):
            offset = page_index * _PAGE_SIZE
            ajax_url = self._ajax_url(origin, offset)
            try:
                decoded = await self.fetch_json(ajax_url)
            except Exception as e:
                Logger.warn(f"{self._log_prefix}: failed to fetch Pabst AJAX page offset={offset}: {e}")
                break
            if not decoded or not isinstance(decoded, str):
                break

            page_events = self._dedupe_routable_events(extract_events(decoded), seen_urls)
            if not page_events:
                break
            events.extend(page_events)

            if len(page_events) < _PAGE_SIZE:
                break

        Logger.info(f"{self._log_prefix}: parsed {len(events)} routable Pabst event(s)")
        return events

    def _origin(self, page_url: str) -> str:
        parts = urlsplit(page_url if "//" in page_url else f"https://{page_url}")
        if not parts.netloc:
            return "https://www.pabsttheatergroup.com"
        return urlunsplit((parts.scheme or "https", parts.netloc, "", "", ""))

    def _ajax_url(self, origin: str, offset: int) -> str:
        return (
            f"{origin}/events/events_ajax/{offset}"
            f"?category=0&venue=0&team=0&per_page={_PAGE_SIZE}&came_from_page=event-list-page"
        )

    def _dedupe_routable_events(self, events: List, seen_urls: set) -> List:
        kept = []
        for event in events:
            if not event.venue_name:
                continue
            key = event.show_page_url or f"{event.title}|{event.date_str}|{event.venue_name}"
            if key in seen_urls:
                continue
            seen_urls.add(key)
            kept.append(event)
        return kept

    async def _filter_comedy(self, events: List) -> List:
        titles = [event.title for event in events if event.title]
        loop = asyncio.get_running_loop()
        kept_titles = await loop.run_in_executor(
            None,
            lambda: select_comedy_titles(
                titles,
                lineup_handler=self._lineup_handler,
                comedian_handler=self._comedian_handler,
                min_popularity=resolve_min_popularity(self.club.source_metadata),
                allowlist=resolve_allowlist(self.club.source_metadata),
                use_known_comedian_match=not bool(
                    (self.club.source_metadata or {}).get("disable_known_comedian_match")
                ),
            ),
        )
        return [event for event in events if event.title in kept_titles]

    async def _upsert_venue(self, loop: asyncio.AbstractEventLoop, venue_payload: dict) -> Optional[Club]:
        if not venue_payload:
            return None
        try:
            return await loop.run_in_executor(
                None,
                serialized_db_call,
                self._club_handler.upsert_discovered_venue,
                venue_payload,
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: upsert_discovered_venue failed for "
                f"'{venue_payload.get('name', '')}': {e}"
            )
            return None
