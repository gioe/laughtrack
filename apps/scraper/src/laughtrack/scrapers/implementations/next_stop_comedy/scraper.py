from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.database.write_lock import serialized_db_call
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import NextStopComedyPageData
from .event import NextStopComedyEvent
from .extractor import extract_event_urls, extract_json_ld_events, normalize_event_id

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
        self._reviewed_ids: set[str] = set()
        self._reviewed_urls: dict[str, str] = {}
        self._reviewed_clubs: dict[str, int] = {}

    async def get_data(self, target: ScrapingTarget) -> Optional[NextStopComedyPageData]:
        await self._load_reviewed_identities()
        html = await self._fetch_page(str(target))
        events = self._reviewed_events([(str(target), event) for event in self._detail_events(str(target), html)])
        return NextStopComedyPageData(event_list=events) if events else None

    async def scrape_async(self) -> list[Show]:
        await self._load_reviewed_identities()
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

        candidates = []
        for url in event_urls:
            html = await self._fetch_page(url)
            for event in self._detail_events(url, html):
                candidates.append((url, event))
        shows: list[Show] = []
        loop = asyncio.get_running_loop()
        # Decide identity conflicts across the complete fetch before venue writes.
        for event in self._reviewed_events(candidates):
            show = await self._event_to_show(loop, event)
            if show is not None:
                shows.append(show)

        Logger.info(
            f"{self._log_prefix}: built {len(shows)} show(s) across Next Stop venues",
            self.logger_context,
        )
        return shows

    def _hold_identity(self, reason: str) -> None:
        message = f"{self._log_prefix}: Next Stop identity review incomplete: {reason}"
        Logger.warn(message)
        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_scrape_error(message)
            # Scrape errors alone only surface for zero-show runs. Mark this
            # target failed so partial successes cannot authorize stale deletion.
            diagnostics.record_fetch_failed()

    def _detail_events(self, url: str, html: Optional[str]) -> list[NextStopComedyEvent]:
        events = extract_json_ld_events(html or "")
        if not events:
            # Missing/cancelled/unparseable detail pages require separate review;
            # absence must never authorize deletion of identified inventory.
            self._hold_identity(f"no verified events at {url}")
        return events

    def _reviewed_events(self, candidates: list[tuple[str, NextStopComedyEvent]]) -> list[NextStopComedyEvent]:
        """Activate only backfilled UUIDs; hold known URLs if native proof vanishes.

        Identified database rows supply UUIDs and their current canonical URLs.
        The repair installs those identities atomically, without a global switch.
        Unreviewed inventory stays on legacy persistence until separately audited.
        """
        reviewed, urls = self._reviewed_ids, self._reviewed_urls
        groups: dict[str, list[NextStopComedyEvent]] = {}
        legacy = []
        blocked = set()
        for requested, event in candidates:
            expected = {urls[url] for url in (requested, event.canonical_event_url, event.event_url) if url in urls}
            if expected and (len(expected) != 1 or event.native_event_id not in expected):
                blocked.update(expected)
                self._hold_identity(f"unverified reviewed event at {requested}")
                continue
            if event.native_event_id in reviewed:
                groups.setdefault(event.native_event_id, []).append(event)
            else:
                legacy.append(event)
        for ident, events in groups.items():
            # Exact payload equality is deliberately conservative: even price or
            # venue disagreement needs a later clean fetch, not an arbitrary pick.
            if ident in blocked or any(event != events[0] for event in events[1:]):
                self._hold_identity(f"conflicting native event {ident}")
                continue
            event = events[0]
            event.source_performance_id = f"next_stop_comedy:{ident}"
            legacy.append(event)
        return legacy

    async def _load_reviewed_identities(self) -> None:
        """Read the promoter's backfilled identities once before fetching a run.

        A failed read aborts the run instead of silently downgrading identified
        events to legacy slot inserts. No source configuration row is required
        for the organizer's virtual scraping source.
        """
        self._reviewed_ids, self._reviewed_urls, self._reviewed_clubs = set(), {}, {}
        if self.club.production_company_id is None:
            return
        query = """SELECT source_performance_id,show_page_url,club_id FROM shows
            WHERE production_company_id=%s AND last_scraped_by='next_stop_comedy'
              AND source_performance_id LIKE 'next_stop_comedy:%%'"""
        loop = asyncio.get_running_loop()
        rows = await loop.run_in_executor(
            None,
            lambda: self._club_handler.execute_with_cursor(
                query, (self.club.production_company_id,), return_results=True
            ),
        )
        for row in rows or []:
            ident = normalize_event_id(row["source_performance_id"].removeprefix("next_stop_comedy:"))
            url = row["show_page_url"]
            if (
                not ident or not url
                or (url in self._reviewed_urls and self._reviewed_urls[url] != ident)
                or (ident in self._reviewed_clubs and self._reviewed_clubs[ident] != row["club_id"])
            ):
                raise ValueError("Ambiguous Next Stop reviewed database identity")
            self._reviewed_ids.add(ident)
            self._reviewed_urls[url] = ident
            self._reviewed_clubs[ident] = row["club_id"]

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
            if event.source_performance_id:
                self._hold_identity(f"unresolved venue for native event {event.native_event_id}")
            Logger.warn(
                f"{self._log_prefix}: could not resolve venue '{event.venue_name}' for {event.event_url}",
                self.logger_context,
            )
            return None
        if event.source_performance_id and self._reviewed_clubs.get(event.native_event_id) != venue_club.id:
            self._hold_identity(f"native event {event.native_event_id} at unexpected club {venue_club.id}")
            return None
        try:
            return event.to_show(venue_club)
        except Exception as e:
            if event.source_performance_id:
                self._hold_identity(f"conversion failed for native event {event.native_event_id}")
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
