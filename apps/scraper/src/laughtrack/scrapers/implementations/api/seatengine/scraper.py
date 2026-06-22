import asyncio
from typing import List, Optional

from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.utils.comedy_filter import (
    is_comedy_filter_enabled,
    resolve_allowlist,
    resolve_min_popularity,
    select_comedy_titles,
)
from laughtrack.ports.scraping import EventListContainer
from .extractor import SeatEngineExtractor
from .transformer import SeatEngineEventTransformer


def _event_title(item: JSONDict) -> str:
    """SeatEngine wraps each show as ``{id, event: {name, ...}}``."""
    return ((item or {}).get("event") or {}).get("name") or ""


class SeatEngineScraper(BaseScraper):
    """
    Scraper for venues that use SeatEngine for event management.

    This scraper reads the club's seatengine_id field and uses the
    SeatEngineClient to fetch all events for that venue via API.

    Mixed-use SeatEngine venues (e.g. P-town cabaret/drag rooms that also
    program stand-up) opt into comedy-only isolation by setting
    ``scraping_sources.metadata.comedy_filter``; dedicated comedy clubs leave it
    unset and ingest the whole calendar unchanged.
    """
    key = 'seatengine'

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)

        # Validate that club has seatengine_id
        if not club.seatengine_id:
            raise ValueError(f"Club {club.name} does not have a seatengine_id configured")

        # Store the venue_id (seatengine_id)
        self.venue_id = club.seatengine_id

        # Initialize the SeatEngine client; pass it to the transformer so that
        # venue_website cached during fetch_events is shared with create_show.
        self.seatengine_client = SeatEngineClient(club, proxy_pool=self.proxy_pool)
        self.transformation_pipeline.register_transformer(
            SeatEngineEventTransformer(club, client=self.seatengine_client)
        )

        # Opt-in comedy isolation for mixed-use venues.
        self._comedy_filter = is_comedy_filter_enabled(self.club.source_metadata)
        self._lineup_handler = LineupHandler() if self._comedy_filter else None
        self._comedian_handler = ComedianHandler() if self._comedy_filter else None

        self.logger_context = club.as_context()

    async def collect_scraping_targets(self) -> List[str]:
        """Use the venue_id as the single logical target for API calls."""
        return [self.venue_id]

    async def get_data(self, target: str) -> Optional[EventListContainer]:
        """Fetch events for the venue and wrap in PageData for pipeline processing.

        Raises:
            CircuitBreakerOpenError: Propagated from the client when the breaker is open.
              ErrorHandler treats this as HIGH severity and does not retry.
            NetworkError: Propagated from the client on non-200 responses.
              ErrorHandler retries with exponential backoff.
        """
        events_data = await self.seatengine_client.fetch_events(self.venue_id)
        if not events_data:
            Logger.warn(
                f"{self._log_prefix}: no events found for venue {self.club.seatengine_id}",
                self.logger_context,
            )
            return SeatEngineExtractor.to_page_data([])
        if self._comedy_filter:
            events_data = await self._filter_comedy(events_data)
        return SeatEngineExtractor.to_page_data(events_data)

    async def _filter_comedy(self, events: List[JSONDict]) -> List[JSONDict]:
        """Keep only events whose title qualifies as comedy (opt-in).

        Mirrors the etix/ticketleap comedy-isolation path: a cheap keyword +
        allowlist pass, then a DB-backed known-comedian fallback for name-only
        touring titles. The handler lookups are blocking, so run them off the
        event loop.
        """
        titles = [_event_title(e) for e in events]
        descriptions = {}
        for e in events:
            event_data = (e or {}).get("event") or {}
            name = event_data.get("name") or ""
            if name and name not in descriptions:
                descriptions[name] = event_data.get("description")
        loop = asyncio.get_running_loop()
        comedy_titles = await loop.run_in_executor(
            None,
            lambda: select_comedy_titles(
                titles,
                lineup_handler=self._lineup_handler,
                comedian_handler=self._comedian_handler,
                descriptions=descriptions,
                min_popularity=resolve_min_popularity(self.club.source_metadata),
                allowlist=resolve_allowlist(self.club.source_metadata),
            ),
        )
        kept = [e for e in events if _event_title(e) in comedy_titles]
        Logger.info(
            f"{self._log_prefix}: comedy filter kept {len(kept)}/{len(events)} event(s)",
            self.logger_context,
        )
        return kept

    def transform_data(self, raw_data: EventListContainer, source_url: str) -> List[Show]:
        return super().transform_data(raw_data, source_url)

    async def discover_urls(self) -> List[str]:
        # Kept for backward compatibility; pipeline uses collect_scraping_targets
        return []

    # Note: old get_data(url) signature replaced by pipeline-compatible get_data(target)

    def validate_configuration(self) -> bool:
        """
        Validate that the club is properly configured for SeatEngine scraping.

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.venue_id:
            Logger.error(f"{self._log_prefix}: missing seatengine_id", self.logger_context)
            return False

        return True
