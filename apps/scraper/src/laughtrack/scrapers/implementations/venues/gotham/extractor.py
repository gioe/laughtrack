"""
Gotham Comedy Club data extraction utilities.

This module provides extraction logic for Gotham Comedy Club's live events
feed — a Cloudflare Worker proxying the venue's Webflow CMS collection.
Each feed item is a single showtime carrying its own Showclix event id, so
ticket enrichment calls the Showclix API directly (no HTML discovery step).
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from laughtrack.core.clients.gotham.models.models import GothamFeedEvent, GothamFeedResponse
from laughtrack.core.clients.showclix.client import ShowclixAPIClient
from laughtrack.core.clients.showclix.models import ShowclixEventData
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.scraper import log_filter_breakdown
from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

from .data import GothamPageData

_SHOWCLIX_BATCH_CONFIG = BatchScrapingConfig(
    max_concurrent=5,
    delay_between_requests=0,
    enable_logging=True,
)


class GothamEventExtractor:
    """
    Extractor for Gotham Comedy Club event data from the live events feed.

    Handles:
    - Feed page fetching (Cloudflare Worker JSON endpoint)
    - Event data extraction and typing (archived/draft and past/unparseable
      showtimes are skipped)
    - Showclix ticket data enrichment via the feed-supplied event ids
    """

    def __init__(self, club, http_session_getter, proxy_pool: Optional[ProxyPool] = None):
        """
        Initialize the extractor.

        Args:
            club: Club entity with configuration
            http_session_getter: Async function to get HTTP session
            proxy_pool: Optional ProxyPool forwarded to Showclix client.
        """
        self.club = club
        self.get_session = http_session_getter
        self.showclix_client = ShowclixAPIClient(club, proxy_pool=proxy_pool)
        self.logger_context = club.as_context()
        self.batch_scraper = BatchScraper(self.logger_context, config=_SHOWCLIX_BATCH_CONFIG)

    def get_headers(self) -> dict:
        """Get headers for the cross-site worker feed request."""
        return BaseHeaders.get_venue_headers(
            venue_type="gotham",
            domain="https://www.gothamcomedyclub.com",
            **{
                "Sec-Fetch-Site": "cross-site",  # Worker is on a different origin
                "Accept": "application/json,*/*",  # JSON preference
            },
        )

    async def extract_events(self, page_url: str) -> Optional[GothamPageData]:
        """
        Extract events from one page of the live events feed.

        Fetch and JSON-decode errors propagate so the BaseScraper retry layer
        can classify them (a Cloudflare 403 here means the whole scrape is
        blocked, not an expected empty month like the old S3 source).

        Args:
            page_url: Feed page URL (e.g., .../items?limit=100&offset=0)

        Returns:
            GothamPageData with extracted events or None if the page has no
            upcoming events
        """
        session = await self.get_session()

        response = await session.get(page_url, headers=self.get_headers())
        response.raise_for_status()
        json_content = response.json()

        # Convert to typed feed response (skips archived/draft items)
        feed = GothamFeedResponse.from_dict(json_content)

        # Keep only upcoming events with parseable start times
        upcoming_events = self._filter_upcoming(feed.events, page_url)

        # Enrich with ticket data
        enriched_events = await self._enrich_events_with_tickets(upcoming_events)

        Logger.info(
            f"GothamEventExtractor [{self.club.name}]: Extracted {len(enriched_events)} upcoming events "
            f"from {page_url} ({len(feed.events)} valid items, total={feed.pagination.total})",
            self.logger_context,
        )

        return GothamPageData(event_list=enriched_events) if enriched_events else None

    def _filter_upcoming(self, events: List[GothamFeedEvent], page_url: str) -> List[GothamFeedEvent]:
        """Drop events whose start time is unparseable or already past.

        The feed retains months of past showtimes; filtering here avoids
        wasting a Showclix API call per dead event.
        """
        now_utc = datetime.now(timezone.utc)
        upcoming: List[GothamFeedEvent] = []
        skipped_past = 0
        skipped_unparseable = 0

        for event in events:
            start = event.start_datetime
            if start is None:
                skipped_unparseable += 1
                Logger.warn(
                    f"GothamEventExtractor [{self.club.name}]: Skipping event {event.name!r} "
                    f"with unparseable start time {event.start!r}",
                    self.logger_context,
                )
                continue
            if start <= now_utc:
                skipped_past += 1
                continue
            upcoming.append(event)

        if skipped_past or skipped_unparseable:
            Logger.info(
                f"GothamEventExtractor [{self.club.name}]: Skipped {skipped_past} past and "
                f"{skipped_unparseable} unparseable-time events from {page_url}",
                self.logger_context,
            )

        return upcoming

    async def _enrich_events_with_tickets(self, events: List[GothamFeedEvent]) -> List[GothamFeedEvent]:
        """
        Enrich GothamFeedEvent objects with ticket data from the Showclix API.

        The feed's ``event-id`` field IS the Showclix event id, so enrichment
        is a single API call per event. Events whose enrichment fails are
        returned unenriched — to_show() still emits a fallback ticket.

        Args:
            events: List of GothamFeedEvent objects

        Returns:
            List of GothamFeedEvent objects enriched with ticket data
        """
        if not events:
            Logger.info(f"GothamEventExtractor [{self.club.name}]: No events to enrich", self.logger_context)
            return events

        try:
            Logger.info(
                f"GothamEventExtractor [{self.club.name}]: Enriching {len(events)} events with Showclix ticket data",
                self.logger_context,
            )

            # Log a standardized breakdown of which events carry a Showclix event id
            _ = log_filter_breakdown(
                events,
                self.logger_context,
                id_getter=lambda e: getattr(e, "event_id", None),
                accept_predicate=lambda e: bool(getattr(e, "event_id", None)),
                label="Showclix enrichment",
                name_getter=lambda e: getattr(e, "name", "n/a"),
                date_getter=lambda e: getattr(e, "start", "n/a"),
            )

            # Separate events with and without Showclix event ids
            events_with_ids = [e for e in events if e.event_id]
            events_without_ids = [e for e in events if not e.event_id]

            for event in events_without_ids:
                Logger.warn(
                    f"GothamEventExtractor [{self.club.name}]: Event missing Showclix event id, "
                    f"skipping enrichment: {event.name} @ {event.start}",
                    self.logger_context,
                )

            if not events_with_ids:
                Logger.info(
                    f"GothamEventExtractor [{self.club.name}]: No events with Showclix event ids found",
                    self.logger_context,
                )
                return events

            # Fetch Showclix data once per unique event id (recurring shows
            # share a parent-id but each showtime has its own event id)
            unique_ids = list(dict.fromkeys(e.event_id for e in events_with_ids))

            async def _fetch_event_data(event_id: str) -> Optional[Tuple[str, ShowclixEventData]]:
                event_data = await self.showclix_client.get_event_data(event_id)
                if not event_data:
                    Logger.warn(
                        f"GothamEventExtractor [{self.club.name}]: Failed to fetch Showclix event data "
                        f"for event_id {event_id}",
                        self.logger_context,
                    )
                    return None
                Logger.info(
                    f"GothamEventExtractor [{self.club.name}]: Successfully fetched Showclix event data "
                    f"for {event_id} - Name: {event_data.event}, Venue: {event_data.venue.venue_name}, "
                    f"Primary Price: ${event_data.get_primary_price()}, "
                    f"Available Tickets: {event_data.get_available_tickets()}",
                    self.logger_context,
                )
                return event_id, event_data

            results = await self.batch_scraper.process_batch(
                unique_ids, _fetch_event_data, description="Showclix enrichment"
            )
            data_by_id = dict(results)

            enriched_events = [
                e.enrich_with_showclix_data(data_by_id[e.event_id]) if e.event_id in data_by_id else e
                for e in events_with_ids
            ]

            # Add events without ids (unenriched)
            enriched_events.extend(events_without_ids)

            Logger.info(
                f"GothamEventExtractor [{self.club.name}]: Successfully processed {len(enriched_events)} events",
                self.logger_context,
            )
            return enriched_events

        except Exception as e:
            Logger.error(
                f"GothamEventExtractor [{self.club.name}]: Error enriching events with tickets: {str(e)}",
                self.logger_context,
            )
            return events
