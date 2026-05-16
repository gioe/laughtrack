"""
Ticketmaster venue scraper using the official Ticketmaster Discovery API.

This scraper leverages the TicketmasterClient to fetch events for venues
that have a ticketmaster_id configured. It provides high-performance,
reliable access to comedy event data through official API endpoints.
"""

from typing import List, Optional

from laughtrack.core.clients.ticketmaster.client import TicketmasterClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.ports.scraping import EventListContainer
from .extractor import TicketmasterExtractor
from .transformer import TicketmasterEventTransformer


class TicketmasterScraper(BaseScraper):
    """
    Scraper for venues using Ticketmaster through official API.

    Features:
    - Uses official Ticketmaster Discovery API
    - Requires club.ticketmaster_id to be configured
    - High-performance (5 requests per second)
    - Reliable structured data from API
    - Automatic rate limiting and error handling

    Known API limitations:
    - Ticket prices (`priceRanges`) are NOT returned by the Discovery API for the
      comedy venues we scrape. A 2026-05-09 audit (TASK-2098) sampled 200+ events
      across both venue id formats — Kov*-prefixed (Punch Line, Laugh Factory,
      Jimmy Kimmel's Comedy Club, The Second City, Cobb's, etc.) and Z*-prefixed
      (Funny Bone chain) — and found 0 events with `priceRanges` populated on
      either the list endpoint (`/events.json?venueId=...`) or the per-event
      detail endpoint (`/events/{id}.json`). The `includeTicketing=yes` query
      parameter does not surface price data either; the `ticketing` block only
      carries an `allInclusivePricing.enabled` flag, never a price. As a result,
      the underlying `TicketmasterClient._extract_ticket_data_from_api` writes
      `price=None` for ~84% of future tickets stamped with `last_scraped_by =
      'live_nation'`. Existing non-null prices in the DB are stale records from
      a prior period when the API exposed `priceRanges` more broadly; the
      idempotent show upsert preserves them when a fresh scrape returns no
      price. Do not re-flag this as a scraper bug — the extraction code is
      correct; the data simply is not in the API response. If a future audit
      sees prices reappearing, the API may have changed and revisiting is fair.
    """
    key = 'live_nation'

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TicketmasterEventTransformer(club))

        # Validate that ticketmaster_id is configured
        if not club.ticketmaster_id:
            raise ValueError(f"Club '{club.name}' must have ticketmaster_id configured " f"to use TicketmasterScraper")

        self.venue_id = club.ticketmaster_id
        self.ticketmaster_client: Optional[TicketmasterClient] = None
        self.logger_context = club.as_context()

    async def discover_urls(self) -> List[str]:
        """
        For Ticketmaster API, we don't discover URLs - we use the API directly.

        Returns:
            List containing the API endpoint (for logging/debugging purposes)
        """
        api_endpoint = f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={self.venue_id}"
        return [api_endpoint]

    async def get_data(self, url: str) -> Optional[EventListContainer]:
        """
        Extract event data from Ticketmaster API.

        The Discovery API list endpoint returns full event objects (dates, attractions,
        venues, priceRanges, sales, etc.) — identical in shape to the detail endpoint.
        Per-event detail fetches are redundant and cause N+1 request patterns that hit
        the 5 req/sec rate limit for large venues. We use the list response directly.

        Args:
            url: API endpoint URL (for compatibility with base class)

        Returns:
            EventListContainer with events from the list response
        """
        try:
            if not self.ticketmaster_client:
                self.ticketmaster_client = TicketmasterClient(self.club, proxy_pool=self.proxy_pool)

            Logger.info(f"{self._log_prefix}: Fetching events for venue {self.venue_id} via Ticketmaster API", self.logger_context)

            events = await self.ticketmaster_client.fetch_events(
                self.venue_id,
                size=200,
                sort="date,asc",
            )

            Logger.info(f"{self._log_prefix}: Successfully fetched {len(events)} events from Ticketmaster API", self.logger_context)

            return TicketmasterExtractor.to_page_data(events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from Ticketmaster API: {e}", self.logger_context)
            return None

    def transform_data(self, raw_data: EventListContainer, source_url: str) -> List[Show]:
        """
        Transform Ticketmaster API data to Show objects using the standard pipeline.

        Returns:
            List of Show objects
        """
        return super().transform_data(raw_data, source_url)

    async def scrape_async(self) -> List[Show]:
        """Use BaseScraper two-phase pipeline."""
        return await super().scrape_async()

    async def close(self):
        """Clean up resources."""
        await super().close()


class FocusedTicketmasterComedyScraper(TicketmasterScraper):
    """Ticketmaster scraper for multi-purpose venues that need comedy-only fetches."""

    key = "ticketmaster_comedy"
    classification_name = "Comedy"
    _ADD_ON_NAME_MARKERS = (
        "add-on",
        "add on",
        "addon",
        "vip club access",
        "vip package",
        "parking",
        "premium parking",
        "fast lane",
    )

    async def discover_urls(self) -> List[str]:
        api_endpoint = (
            "https://app.ticketmaster.com/discovery/v2/events.json"
            f"?venueId={self.venue_id}&classificationName={self.classification_name}"
        )
        return [api_endpoint]

    async def get_data(self, url: str) -> Optional[EventListContainer]:
        try:
            if not self.ticketmaster_client:
                self.ticketmaster_client = TicketmasterClient(self.club, proxy_pool=self.proxy_pool)

            Logger.info(
                f"{self._log_prefix}: Fetching {self.classification_name} events for venue "
                f"{self.venue_id} via Ticketmaster API",
                self.logger_context,
            )

            events = await self.ticketmaster_client.fetch_events(
                self.venue_id,
                size=200,
                sort="date,asc",
                classificationName=self.classification_name,
            )
            focused_events = [event for event in events if self._is_focused_comedy_event(event)]

            Logger.info(
                f"{self._log_prefix}: Kept {len(focused_events)} of {len(events)} "
                f"Ticketmaster {self.classification_name} events",
                self.logger_context,
            )

            return TicketmasterExtractor.to_page_data(focused_events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting focused Ticketmaster data: {e}", self.logger_context)
            return None

    @classmethod
    def _is_focused_comedy_event(cls, event: dict) -> bool:
        return TicketmasterEventTransformer._is_comedy_event(event) and not cls._is_add_on_event(event)

    @classmethod
    def _is_add_on_event(cls, event: dict) -> bool:
        name = str(event.get("name") or "").lower()
        if any(marker in name for marker in cls._ADD_ON_NAME_MARKERS):
            return True

        event_type = str(event.get("type") or "").lower()
        if "add-on" in event_type or "addon" in event_type:
            return True

        return False


# Factory function for creating Ticketmaster scrapers
def create_ticketmaster_scraper(club: Club) -> TicketmasterScraper:
    """
    Factory function to create a TicketmasterScraper.

    Args:
        club: Club instance with ticketmaster_id configured

    Returns:
        Configured TicketmasterScraper instance

    Raises:
        ValueError: If club.ticketmaster_id is not configured
    """
    return TicketmasterScraper(club)
