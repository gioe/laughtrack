"""
TicketmasterNationalScraper: queries the Ticketmaster Discovery API for US
comedy events at the national level — no per-venue IDs required.

For each event returned:
- Upserts a clubs row for the venue (storing ticketmaster_id, scraper='live_nation').
- Converts the event to a Show via TicketmasterClient.create_show().

Deduplicates correctly against shows already ingested by venue-specific TM
scrapers: the clubs UPSERT conflicts on name (COALESCE preserves existing
ticketmaster_id/scraper), and show-level dedup is handled by insert_shows().

Triggered by a single clubs row with scraper='ticketmaster_national'.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urlencode

from laughtrack.core.clients.ticketmaster.client import TicketmasterClient
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.scrapers.base.base_scraper import BaseScraper


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
            return shows
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

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
            venue_events = [
                e for e in page_events
                if e.get("_embedded", {}).get("venues")
            ]
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
        """Group events by venue, upsert clubs, convert to Shows."""
        venue_groups: dict = defaultdict(list)
        for event in api_events:
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
                club = await loop.run_in_executor(
                    None, self._club_handler.upsert_for_ticketmaster_venue, venue
                )
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
                show = client.create_show(event)
                if show:
                    shows.append(show)

        return shows
