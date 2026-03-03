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


class TicketmasterScraper(BaseScraper):
    """
    Scraper for venues using Ticketmaster through official API.

    Features:
    - Uses official Ticketmaster Discovery API
    - Requires club.ticketmaster_id to be configured
    - High-performance (5 requests per second)
    - Reliable structured data from API
    - Automatic rate limiting and error handling
    """
    key = 'live_nation'

    def __init__(self, club: Club):
        super().__init__(club)

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
        Extract event data from Ticketmaster API with detailed event information.

        This method implements a two-step process:
        1. Fetch initial events list for the venue
        2. Fetch detailed information for each event using event IDs

        Args:
            url: API endpoint URL (for compatibility with base class)

        Returns:
            Dictionary with detailed events data from API
        """
        try:
            # Use the TicketmasterClient to fetch events
            if not self.ticketmaster_client:
                self.ticketmaster_client = TicketmasterClient(self.club)

            Logger.info(f"Fetching events for venue {self.venue_id} via Ticketmaster API", self.logger_context)

            # Step 1: Fetch events list with comedy classification
            events = await self.ticketmaster_client.fetch_events(
                self.venue_id,
                classificationName="comedy",  # Focus on comedy events
                size=200,  # Maximum events per request
                sort="date,asc",  # Sort by date
            )

            Logger.info(f"Successfully fetched {len(events)} events from Ticketmaster API", self.logger_context)

            if not events:
                return TicketmasterExtractor.to_page_data([])

            # Step 2: Extract event IDs and fetch detailed information for each event
            detailed_events = []
            event_ids = [event.get("id") for event in events if event.get("id")]

            Logger.info(f"Fetching detailed information for {len(event_ids)} events", self.logger_context)

            # Fetch event details with rate limiting
            for i, event_id in enumerate(event_ids):
                try:
                    if not event_id:
                        Logger.warn(f"Skipping event with None event_id at index {i}", self.logger_context)
                        continue
                    Logger.info(f"Fetching details for event {i+1}/{len(event_ids)}: {event_id}", self.logger_context)
                    event_details = await self.ticketmaster_client.get_event_details(event_id)
                    if event_details:
                        detailed_events.append(event_details)
                        Logger.info(
                            f"Successfully fetched details for event: {event_details.get('name', event_id)}",
                            self.logger_context,
                        )
                    else:
                        Logger.warn(f"Failed to fetch details for event: {event_id}", self.logger_context)
                except Exception as e:
                    Logger.error(f"Error fetching details for event {event_id}: {str(e)}", self.logger_context)
                    continue

            Logger.info(
                f"Successfully fetched detailed information for {len(detailed_events)} out of {len(event_ids)} events",
                self.logger_context,
            )

            return TicketmasterExtractor.to_page_data(detailed_events)

        except Exception as e:
            Logger.error(f"Error extracting data from Ticketmaster API: {e}", self.logger_context)
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
