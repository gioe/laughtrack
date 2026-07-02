from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.database.write_lock import serialized_db_call
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import NextStopComedyPageData
from .event import NextStopComedyEvent
from .extractor import extract_event_urls, extract_json_ld_events

_BASE_URL = "https://www.nextstopcomedy.com"
_EVENTS_URL = f"{_BASE_URL}/events"
_PAGE_SIZE = 48
_MAX_PAGES = 25


class NextStopComedyScraper(BaseScraper):
    """Roving promoter scraper for nextstopcomedy.com events."""

    key = "next_stop_comedy"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()

    async def get_data(self, target: ScrapingTarget) -> Optional[NextStopComedyPageData]:
        html = await self._fetch_page(str(target))
        events = extract_json_ld_events(html or "")
        return NextStopComedyPageData(event_list=events) if events else None

    async def scrape_async(self) -> list[Show]:
        listing_url = self.club.scraping_url or _EVENTS_URL
        listing_html = await self._fetch_page(listing_url)
        if not listing_html:
            self._warn_empty_extraction(listing_url, html=listing_html)
            return []

        api_events = await self._collect_api_events()
        event_urls = extract_event_urls(listing_html, api_events)
        if not event_urls:
            self._warn_empty_extraction(listing_url, subject="event URLs", html=listing_html)
            return []

        Logger.info(
            f"{self._log_prefix}: found {len(event_urls)} Next Stop event detail URL(s)",
            self.logger_context,
        )

        shows: list[Show] = []
        loop = asyncio.get_running_loop()
        for url in event_urls:
            html = await self._fetch_page(url)
            for event in extract_json_ld_events(html or ""):
                show = await self._event_to_show(loop, event)
                if show is not None:
                    shows.append(show)

        Logger.info(
            f"{self._log_prefix}: built {len(shows)} show(s) across Next Stop venues",
            self.logger_context,
        )
        return shows

    async def _collect_api_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        offset = _PAGE_SIZE
        for _ in range(_MAX_PAGES):
            payload = await self._fetch_json(f"{_BASE_URL}/api/events/load-more?offset={offset}")
            page_events = payload.get("events") if isinstance(payload, dict) else None
            if not isinstance(page_events, list):
                break
            events.extend(item for item in page_events if isinstance(item, dict))
            if not payload.get("hasMore"):
                break
            next_offset = payload.get("nextOffset")
            if not isinstance(next_offset, int) or next_offset <= offset:
                offset += _PAGE_SIZE
            else:
                offset = next_offset
        return events

    async def _event_to_show(self, loop: asyncio.AbstractEventLoop, event: NextStopComedyEvent) -> Optional[Show]:
        venue_club = await self._upsert_venue(loop, event)
        if venue_club is None:
            Logger.warn(
                f"{self._log_prefix}: could not resolve venue '{event.venue_name}' for {event.event_url}",
                self.logger_context,
            )
            return None
        try:
            return event.to_show(venue_club)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: to_show failed for '{event.title}' at '{event.venue_name}': {e}",
                self.logger_context,
            )
            return None

    async def _upsert_venue(self, loop: asyncio.AbstractEventLoop, event: NextStopComedyEvent) -> Optional[Club]:
        try:
            return await loop.run_in_executor(
                None,
                serialized_db_call,
                self._club_handler.upsert_discovered_venue,
                event.venue_payload(),
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: upsert_discovered_venue failed for '{event.venue_name}': {e}",
                self.logger_context,
            )
            return None

    async def _fetch_page(self, url: str) -> Optional[str]:
        return await self.fetch_html(url, scraper_key=self.key)

    async def _fetch_json(self, url: str) -> dict[str, Any]:
        text = await self._fetch_page(url)
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            Logger.warn(f"{self._log_prefix}: invalid JSON from {url}", self.logger_context)
            return {}
        return parsed if isinstance(parsed, dict) else {}
