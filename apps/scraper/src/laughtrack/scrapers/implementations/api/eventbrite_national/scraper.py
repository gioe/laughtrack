"""
EventbriteNationalScraper: queries the Eventbrite comedy category at the
national US level — no per-venue org ID required.

For each event returned:
- Upserts a clubs row for the venue (storing eventbrite_id, scraper='eventbrite').
- Converts the event to a Show via EventbriteEvent.to_show().

The scraper is triggered by a single clubs row with scraper='eventbrite_national';
ScrapingService orchestration is unchanged.
"""

import asyncio
from collections import defaultdict
from typing import List, Optional
from urllib.parse import urlencode

from laughtrack.core.clients.eventbrite.models import EventbriteListEventsResponse
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.eventbrite import EventbriteEvent as DomainEventbriteEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper


class EventbriteNationalScraper(BaseScraper):
    """
    Platform-level Eventbrite scraper that queries the comedy category
    nationally (no per-venue org ID required).

    Triggered by a single clubs row with scraper='eventbrite_national'.
    Discovers venues via the Eventbrite search API, upserts club rows for
    newly-seen venues, and returns Shows for all discovered events.
    """

    key = "eventbrite_national"

    # Eventbrite "Comedy" subcategory under "Performing & Visual Arts" (103)
    _COMEDY_SUBCATEGORY_ID = "103003"
    _BASE_API_URL = "https://www.eventbriteapi.com/v3"
    _REQUEST_TIMEOUT = 30

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()

    # ------------------------------------------------------------------ #
    # BaseScraper pipeline                                                 #
    # ------------------------------------------------------------------ #

    async def collect_scraping_targets(self) -> List[str]:
        """Single logical target representing the national comedy category."""
        return ["national"]

    async def get_data(self, target: str) -> Optional[EventListContainer]:
        """Not used: scrape_async is fully overridden for multi-venue logic."""
        return None  # pragma: no cover

    async def scrape_async(self) -> List[Show]:
        """Override: discover venues nationally, upsert clubs, produce Shows."""
        try:
            api_events = await self._fetch_national_comedy_events()
            if not api_events:
                Logger.info("EventbriteNational: no comedy events returned", self.logger_context)
                return []

            Logger.info(
                f"EventbriteNational: fetched {len(api_events)} comedy events",
                self.logger_context,
            )
            shows = await self._process_events(api_events)
            Logger.info(
                f"EventbriteNational: produced {len(shows)} shows",
                self.logger_context,
            )
            return shows
        except Exception as e:
            Logger.error(f"EventbriteNationalScraper failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _fetch_national_comedy_events(self) -> list:
        """Paginate through the Eventbrite search API for US comedy events."""
        token = ConfigManager.get_config("api", "eventbrite_token")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        base_params = {
            "subcategories": self._COMEDY_SUBCATEGORY_ID,
            "location.country": "US",
            "status": "live",
            "only_public": "true",
            "expand": "venue",
        }

        events: list = []
        continuation: Optional[str] = None

        while True:
            params = dict(base_params)
            if continuation:
                params["continuation"] = continuation

            url = f"{self._BASE_API_URL}/events/search/?{urlencode(params)}"
            data = await self.fetch_json(url, headers=headers, timeout=self._REQUEST_TIMEOUT)
            if not data:
                break

            response = EventbriteListEventsResponse.from_dict(data)
            if not response or not response.events:
                break

            # Only keep events with a physical venue
            venue_events = [e for e in response.events if e.venue and e.venue.id]
            events.extend(venue_events)

            if not response.pagination or not response.pagination.has_more_items:
                break
            continuation = response.pagination.continuation

        return events

    async def _process_events(self, api_events: list) -> List[Show]:
        """Group events by venue, upsert clubs, convert to Shows."""
        venue_groups: dict = defaultdict(list)
        for event in api_events:
            venue_groups[event.venue.id].append(event)

        loop = asyncio.get_event_loop()
        shows: List[Show] = []

        for venue_id, group in venue_groups.items():
            venue = group[0].venue
            try:
                club = await loop.run_in_executor(
                    None, self._club_handler.upsert_for_eventbrite_venue, venue
                )
            except Exception as exc:
                Logger.error(
                    f"EventbriteNational: failed to upsert club for venue {venue_id}: {exc}",
                    self.logger_context,
                )
                continue

            if club is None:
                Logger.warn(
                    f"EventbriteNational: upsert returned None for venue {venue_id}",
                    self.logger_context,
                )
                continue

            for api_event in group:
                domain_event = DomainEventbriteEvent.from_api_model(api_event)
                show = domain_event.to_show(club)
                if show:
                    shows.append(show)

        return shows
