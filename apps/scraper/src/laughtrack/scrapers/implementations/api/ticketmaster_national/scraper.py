"""
TicketmasterNationalScraper: queries the Ticketmaster Discovery API for US
comedy events at the national level — no per-venue IDs required.

For each event returned:
- Upserts a clubs row for the venue (storing ticketmaster_id, scraper='live_nation').
- Converts the event to a Show via TicketmasterClient.create_show().

Deduplicates correctly against shows already ingested by venue-specific TM
scrapers: the clubs UPSERT resolves existing clubs by
scraping_sources.ticketmaster_id before falling back to name for brand-new
venues, and show-level dedup is handled by insert_shows().

Triggered by a single clubs row with scraper='ticketmaster_national'.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urlencode, urlparse

from laughtrack.core.clients.ticketmaster.client import TicketmasterClient
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.scrapers.base.base_scraper import BaseScraper

_TICKETWEB_HTML_KEY = "_ticketweb_html"


class TicketmasterNationalScraper(BaseScraper):
    """
    Platform-level Ticketmaster scraper that queries the comedy genre
    nationally (no per-venue ID required).

    Triggered by a single clubs row with scraper='ticketmaster_national'.
    Discovers venues via the Ticketmaster Discovery API, upserts club rows for
    newly-seen venues, and returns Shows for all discovered events.
    """

    key = "ticketmaster_national"

    _BASE_URL = "https://app.ticketmaster.com/discovery/v2"
    _REQUEST_TIMEOUT = 30
    _PAGE_SIZE = 200

    # The Discovery API rejects deep paging: (page * size) must be < 1000
    # (error DIS1035). With size=200 only pages 0-4 are reachable, so a single
    # national query (sorted date,asc) silently truncates to the soonest ~1000
    # events — dropping ~90% of the catalog and every show booked past the next
    # few weeks (arenas/theatres like MSG). We therefore shard the horizon into
    # date windows small enough that each stays under the cap and union the
    # results. See _fetch_window / _fetch_national_comedy_events.
    _MAX_PAGES_PER_WINDOW = 1000 // _PAGE_SIZE  # = 5 (pages 0-4)
    _HORIZON_DAYS = 180
    _WINDOW_DAYS = 10

    # A national scrape produces ~10k shows — far more than the per-club
    # pipeline's single insert_club_result (capped by _DB_WRITE_TIMEOUT) can
    # persist in one call. We persist them ourselves in chunks here and return
    # [] from scrape_async so the pipeline has nothing left to write. Chunking
    # also makes progress durable: a mid-run failure keeps already-committed
    # chunks instead of losing all ~10k shows.
    _PERSIST_CHUNK_SIZE = 1000

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()
        self._api_key = ConfigManager.get_config("api", "ticketmaster_api_key")

    # ------------------------------------------------------------------ #
    # BaseScraper pipeline                                                 #
    # ------------------------------------------------------------------ #

    async def collect_scraping_targets(self) -> List[str]:
        """Single logical target representing the national comedy category."""
        return ["national"]

    async def get_data(self, target: str) -> None:
        """Not used: scrape_async is fully overridden for multi-venue logic."""
        return None  # pragma: no cover

    async def scrape_async(self) -> List[Show]:
        """Override: discover venues nationally, upsert clubs, produce Shows."""
        try:
            api_events = await self._fetch_national_comedy_events()
            if not api_events:
                Logger.info(f"{self._log_prefix}: no comedy events returned", self.logger_context)
                return []

            Logger.info(
                f"{self._log_prefix}: fetched {len(api_events)} comedy events",
                self.logger_context,
            )
            shows = await self._process_events(api_events)
            Logger.info(
                f"{self._log_prefix}: produced {len(shows)} shows",
                self.logger_context,
            )
            # Persist here in chunks, then return [] — the standard per-club
            # persist path cannot write this volume within _DB_WRITE_TIMEOUT.
            await self._persist_in_chunks(shows)
            return []
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    async def _persist_in_chunks(self, shows: List[Show]) -> int:
        """Persist shows in fixed-size chunks via ShowService, so each DB write
        stays small (under the pipeline's persist timeout) and progress is
        durable across the ~10k-show national batch.

        Shows carry their own club_id (set by create_show), so batching by count
        attributes each show to its correct venue regardless of grouping.
        """
        if not shows:
            return 0

        from laughtrack.core.entities.show.service import ShowService

        service = ShowService()
        loop = asyncio.get_running_loop()
        persisted = 0
        for start in range(0, len(shows), self._PERSIST_CHUNK_SIZE):
            chunk = shows[start : start + self._PERSIST_CHUNK_SIZE]
            try:
                await loop.run_in_executor(
                    None,
                    lambda c=chunk: service.insert_shows(c, club_name=self._club.name, scraper_key=self.key),
                )
                persisted += len(chunk)
                Logger.info(
                    f"{self._log_prefix}: persisted {persisted}/{len(shows)} shows",
                    self.logger_context,
                )
            except Exception as exc:
                Logger.error(
                    f"{self._log_prefix}: chunk persist failed at offset {start}: {exc}",
                    self.logger_context,
                )
        return persisted

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _fetch_national_comedy_events(self) -> list:
        """Fetch US comedy events across the full horizon via date-window sharding.

        Slices the horizon into windows small enough that each stays under the
        Discovery API's deep-paging cap (DIS1035), fetches each window, and
        unions the results — deduped by event id across overlapping window
        boundaries. This is what lets us reach the full catalog (incl. arena/
        theatre shows booked months out, like MSG) instead of only the soonest
        ~1000 events a single national query can page through.
        """
        now = datetime.utcnow()
        horizon_end = now + timedelta(days=self._HORIZON_DAYS)

        events_by_id: dict = {}
        window_start = now
        while window_start < horizon_end:
            window_end = min(window_start + timedelta(days=self._WINDOW_DAYS), horizon_end)
            window_events = await self._fetch_window(window_start, window_end)
            for event in window_events:
                event_id = event.get("id")
                if event_id:
                    events_by_id[event_id] = event
            window_start = window_end

        return list(events_by_id.values())

    async def _fetch_window(self, start: datetime, end: datetime) -> list:
        """Paginate one [start, end) date window of US comedy events.

        Stops at _MAX_PAGES_PER_WINDOW to stay under the DIS1035 cap. If a
        window itself holds more events than the cap can reach, logs a warning
        so the window size can be tightened — under normal volume a 10-day
        window stays well under 1000 events.
        """
        base_params = {
            "apikey": self._api_key,
            "classificationName": "Comedy",
            "countryCode": "US",
            "size": self._PAGE_SIZE,
            "sort": "date,asc",
            "startDateTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        events: list = []
        page = 0
        while page < self._MAX_PAGES_PER_WINDOW:
            params = {**base_params, "page": page}
            url = f"{self._BASE_URL}/events.json?{urlencode(params)}"

            data = await self.fetch_json(url, timeout=self._REQUEST_TIMEOUT)
            if not data:
                break

            page_events = data.get("_embedded", {}).get("events", [])
            if not page_events:
                break

            # Only keep events that have at least one embedded venue
            venue_events = [e for e in page_events if e.get("_embedded", {}).get("venues")]
            events.extend(venue_events)

            pagination = data.get("page", {})
            total_elements = pagination.get("totalElements", 0)
            if page == 0 and total_elements > 1000:
                Logger.warn(
                    f"{self._log_prefix}: window {start.date()}..{end.date()} has "
                    f"{total_elements} events (>1000 cap) — narrow _WINDOW_DAYS to avoid truncation",
                    self.logger_context,
                )

            total_pages = pagination.get("totalPages", 1)
            if page + 1 >= total_pages:
                break
            page += 1

        return events

    async def _process_events(self, api_events: list) -> List[Show]:
        """Group events by venue, upsert clubs, convert to Shows.

        Filters out non-comedy events first. The Discovery API's
        classificationName=Comedy is loose — it also returns multi-genre events
        (e.g. music festivals with one comedy act on the bill) whose own
        classification is Music/Sports. The venue-specific TM scrapers drop
        these via TicketmasterEventTransformer._is_comedy_event, but the national
        path calls create_show directly and bypasses that transformer. Apply the
        same gate here; without it every attraction on a music festival's bill is
        persisted as a 'comedian' (e.g. Bruce Springsteen on a Music-tagged
        festival).
        """
        from laughtrack.scrapers.implementations.api.ticketmaster.transformer import (  # noqa: PLC0415
            TicketmasterEventTransformer,
        )

        comedy_events = [e for e in api_events if TicketmasterEventTransformer._is_comedy_event(e)]
        dropped = len(api_events) - len(comedy_events)
        if dropped:
            Logger.info(
                f"{self._log_prefix}: dropped {dropped} non-comedy event(s) "
                f"(multi-genre/music events the API returned under Comedy)",
                self.logger_context,
            )

        venue_groups: dict = defaultdict(list)
        for event in comedy_events:
            venues = event.get("_embedded", {}).get("venues", [])
            if venues:
                venue_id = venues[0].get("id")
                if venue_id:
                    venue_groups[venue_id].append(event)

        loop = asyncio.get_running_loop()
        shows: List[Show] = []

        for venue_id, group in venue_groups.items():
            venue = group[0].get("_embedded", {}).get("venues", [{}])[0]
            try:
                club = await loop.run_in_executor(None, self._club_handler.upsert_for_ticketmaster_venue, venue)
            except Exception as exc:
                Logger.error(
                    f"{self._log_prefix}: failed to upsert club for venue {venue_id}: {exc}",
                    self.logger_context,
                )
                continue

            if club is None:
                Logger.warn(
                    f"{self._log_prefix}: upsert returned None for venue {venue_id}",
                    self.logger_context,
                )
                continue

            client = TicketmasterClient(club, api_key=self._api_key, proxy_pool=self.proxy_pool)
            for event in group:
                enriched_event = await self._attach_ticketweb_html(event)
                show = client.create_show(enriched_event)
                if show:
                    shows.append(show)

        return shows

    async def _attach_ticketweb_html(self, event: dict) -> dict:
        """Fetch TicketWeb detail HTML for Ticketmaster-discovered TicketWeb URLs.

        Ticketmaster Discovery can report ``priceRanges: 0`` for TicketWeb
        events even when the TicketWeb page is paid or unavailable. The HTML is
        the pricing authority for these URLs; failures fall back to API data so
        the event is still retained.
        """
        event_url = event.get("url", "")
        hostname = urlparse(event_url or "").hostname or ""
        if not hostname.lower().endswith("ticketweb.com"):
            return event

        try:
            html = await self.fetch_html(event_url, timeout=self._REQUEST_TIMEOUT)
        except Exception as exc:
            Logger.warn(
                f"{self._log_prefix}: failed to fetch TicketWeb detail HTML for {event_url}: {exc}",
                self.logger_context,
            )
            return event

        if not html:
            return event

        enriched_event = dict(event)
        enriched_event[_TICKETWEB_HTML_KEY] = html
        return enriched_event
