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
    _MAX_PAGES = 50
    _PAGE_SIZE = 200

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
        """Paginate through the Ticketmaster Discovery API for US comedy events."""
        now = datetime.utcnow()
        start_dt = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_dt = (now + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")

        base_params = {
            "apikey": self._api_key,
            "classificationName": "Comedy",
            "countryCode": "US",
            "size": self._PAGE_SIZE,
            "sort": "date,asc",
            "startDateTime": start_dt,
            "endDateTime": end_dt,
        }

        events: list = []
        page = 0

        while page < self._MAX_PAGES:
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
            total_pages = pagination.get("totalPages", 1)
            if page + 1 >= total_pages:
                break
            page += 1

        if page >= self._MAX_PAGES:
            Logger.warn(
                f"{self._log_prefix}: reached MAX_PAGES ({self._MAX_PAGES}) — pagination truncated",
                self.logger_context,
            )

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
