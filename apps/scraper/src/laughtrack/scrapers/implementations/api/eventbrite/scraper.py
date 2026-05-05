"""
EventbriteScraper for venues using Eventbrite's API.

This scraper has two operating modes:

- **Single-venue mode** — the configured Eventbrite source URL points at a venue
  (no ``/o/`` segment). Every event in the feed belongs to that venue, so the
  standard BaseScraper pipeline applies: fetch events, transform each one with
  the configured ``EventbriteEventTransformer`` whose ``club`` is the scraping
  Club, and produce one Show per event.

- **Organizer mode** — the source URL contains ``/o/`` (an Eventbrite organizer
  feed). A single organizer can run shows at many different venues, so the
  scraper bypasses the standard transformer pipeline and instead:
    1. fetches the organizer's events with ``expand=venue`` already applied by
       the client,
    2. groups events by ``venue.id``,
    3. upserts a per-venue ``clubs`` row via
       ``ClubHandler.upsert_for_eventbrite_venue`` for each distinct venue,
    4. produces a Show per event whose ``club_id`` is the per-venue club id.
  Production-company stamping (``production_company_id``) is applied later by
  the scraping orchestrator on every Show in the result, regardless of which
  per-venue club each Show points at.
"""

import asyncio
from collections import defaultdict
from typing import List, Optional, Tuple

from laughtrack.core.clients.eventbrite.client import EventbriteClient
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.database.write_lock import serialized_db_call
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from .extractor import EventbriteExtractor
from .transformer import EventbriteEventTransformer


class EventbriteScraper(BaseScraper):
    """
    Scraper for venues that use Eventbrite for event management.

    Reads the club's eventbrite_id field and uses :class:`EventbriteClient` to
    fetch events. When the configured source URL is an organizer feed (contains
    ``/o/``), per-event venue routing is enabled via :meth:`_scrape_organizer_async`.
    """

    key = 'eventbrite'

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(EventbriteEventTransformer(club))

        # Validate that club has eventbrite_id
        if not club.eventbrite_id:
            raise ValueError(f"Club {club.name} does not have an eventbrite_id configured")

        # Initialize the Eventbrite client
        self.eventbrite_client = EventbriteClient(club, proxy_pool=self.proxy_pool)

        self.logger_context = club.as_context()

        self._club_handler = ClubHandler()

    @property
    def _is_organizer_mode(self) -> bool:
        """True when the configured source URL targets an Eventbrite organizer feed.

        Organizer feeds (``eventbrite.com/o/...``) span many venues; per-event
        venue routing is required so each Show is attached to its own ``clubs``
        row. The substring check mirrors ``_extract_eventbrite_organizer_id`` in
        services/scraping so a URL that activates organizer mode here is the
        same one the orchestrator's synthetic-proxy builder accepts.
        """
        return "eventbrite.com/o/" in (self.club.scraping_url or "")

    async def collect_scraping_targets(self) -> List[str]:
        """API-based: single logical target representing the venue/organizer ID."""
        return [self.club.eventbrite_id] if self.club.eventbrite_id else []

    async def get_data(self, target: str) -> Optional[EventListContainer]:
        """Fetch Eventbrite events and wrap into PageData container.

        Only used by the standard pipeline in single-venue mode. In organizer
        mode :meth:`scrape_async` is overridden so this method is never reached.
        """
        try:
            if not target:
                return None
            Logger.info(f"{self._log_prefix}: Fetching Eventbrite events for venue {target}", self.logger_context)
            events = await self.eventbrite_client.fetch_all_events()
            if events is None:
                Logger.warn(f"{self._log_prefix}: Network failure fetching Eventbrite events for {target}", self.logger_context)
                return None
            return EventbriteExtractor.to_page_data(events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error fetching Eventbrite data: {e}", self.logger_context)
            return None

    async def scrape_async(self) -> List[Show]:
        """Dispatch to organizer-mode routing when the source URL is a ``/o/`` feed."""
        if not self._is_organizer_mode:
            return await super().scrape_async()
        try:
            shows = await self._scrape_organizer_async()
            Logger.info(
                f"{self._log_prefix}: Scraped {len(shows)} total shows",
                self.logger_context,
            )
            return shows
        except Exception as e:
            Logger.error(f"{self._log_prefix}: Scraping failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    @staticmethod
    def _venue_dedupe_key(api_venue) -> Optional[Tuple[str, str, str]]:
        """Build a (name, city, state) dedupe key for the per-organizer upsert pass.

        Returns ``None`` for events whose ``_api_venue`` is missing or has no
        usable name — those events can't be routed to a per-venue club and are
        dropped upstream with a single aggregate warning. Name is required
        because the SQL UPSERT in ``upsert_for_eventbrite_venue`` keys on
        ``clubs.name``; city/state default to empty strings when absent so two
        events that share a name and have nothing else fill in still collapse
        to one group rather than splitting on missing-vs-present address data.
        """
        if api_venue is None:
            return None
        name = getattr(api_venue, "name", None)
        if not name or not str(name).strip():
            return None
        address = getattr(api_venue, "address", None)
        city = getattr(address, "city", None) if address is not None else None
        region = getattr(address, "region", None) if address is not None else None
        return (
            str(name).strip().lower(),
            str(city or "").strip().lower(),
            str(region or "").strip().lower(),
        )

    async def _scrape_organizer_async(self) -> List[Show]:
        """Organizer-mode pipeline: group events by venue, upsert per-venue clubs.

        Mirrors the per-venue routing pattern previously used by the retired
        EventbriteNationalScraper — each distinct venue triggers one
        ``upsert_for_eventbrite_venue`` call, and every event at that venue
        becomes a Show whose ``club_id`` points at the per-venue club.
        """
        events = await self.eventbrite_client.fetch_all_events()
        if not events:
            Logger.info(f"{self._log_prefix}: organizer feed returned no events", self.logger_context)
            return []

        # Group events by normalized (name, city, state). Eventbrite emits
        # multiple distinct venue.id values for the same physical venue
        # (TASK-1900: production_company id=2's organizer feed returned 4
        # events with 4 distinct venue_ids but only 2 distinct physical
        # venues), so grouping by venue.id over-fragments and triggers one
        # redundant upsert_for_eventbrite_venue call per duplicate id —
        # each acquiring the process-wide serialized_db_call write lock.
        # The SQL UPSERT keys on clubs.name as a backstop, but the dedupe
        # avoids the redundant lock acquisitions entirely.
        venue_groups: dict = defaultdict(list)
        events_without_venue = 0
        for event in events:
            api_venue = event._api_venue
            key = self._venue_dedupe_key(api_venue)
            if key is None:
                events_without_venue += 1
                continue
            venue_groups[key].append(event)

        if events_without_venue:
            Logger.warn(
                f"{self._log_prefix}: {events_without_venue} event(s) had no venue data — skipping",
                self.logger_context,
            )

        if not venue_groups:
            return []

        loop = asyncio.get_running_loop()

        async def _upsert_one(venue_key, group) -> List[Show]:
            api_venue = group[0]._api_venue
            venue_label = getattr(api_venue, "name", None) or str(venue_key)
            try:
                venue_club = await loop.run_in_executor(
                    None,
                    serialized_db_call,
                    self._club_handler.upsert_for_eventbrite_venue,
                    api_venue,
                )
            except Exception as exc:
                Logger.error(
                    f"{self._log_prefix}: failed to upsert club for venue '{venue_label}': {exc}",
                    self.logger_context,
                )
                return []

            if venue_club is None:
                Logger.warn(
                    f"{self._log_prefix}: upsert returned None for venue '{venue_label}' — skipping {len(group)} event(s)",
                    self.logger_context,
                )
                return []

            # to_show is wrapped in try/except so an unexpected raise on a
            # single event does not propagate out of asyncio.gather and
            # cancel sibling _upsert_one tasks — the previous sequential
            # for-loop completed already-iterated venues, and that
            # regression surface is preserved here.
            group_shows: List[Show] = []
            for event in group:
                try:
                    show = event.to_show(venue_club)
                except Exception as exc:
                    Logger.error(
                        f"{self._log_prefix}: to_show failed for venue '{venue_label}' event "
                        f"'{getattr(event, 'name', '?')}': {exc}",
                        self.logger_context,
                    )
                    continue
                if show:
                    group_shows.append(show)
            return group_shows

        # Run per-venue upserts concurrently. serialized_db_call still serializes
        # the actual writes through the process-wide DB lock, so concurrency
        # only parallelizes the executor dispatch and Show construction —
        # overlapping clubs upserts are still impossible.
        per_venue_shows = await asyncio.gather(
            *[_upsert_one(key, group) for key, group in venue_groups.items()]
        )
        shows: List[Show] = [show for group_shows in per_venue_shows for show in group_shows]

        Logger.info(
            f"{self._log_prefix}: organizer feed produced {len(shows)} show(s) across {len(venue_groups)} venue(s)",
            self.logger_context,
        )
        return shows
