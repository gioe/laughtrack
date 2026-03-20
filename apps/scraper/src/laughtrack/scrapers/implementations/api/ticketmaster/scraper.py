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

            Logger.info(f"Fetching events for venue {self.venue_id} via Ticketmaster API", self.logger_context)

            events = await self.ticketmaster_client.fetch_events(
                self.venue_id,
                classificationName="comedy",
                size=200,
                sort="date,asc",
            )

            Logger.info(f"Successfully fetched {len(events)} events from Ticketmaster API", self.logger_context)

            return TicketmasterExtractor.to_page_data(events)

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
