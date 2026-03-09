"""
EventbriteScraper for venues using Eventbrite's API.

This scraper uses the Club's eventbrite_id field to fetch events directly
from Eventbrite's API and runs through the BaseScraper pipeline.
"""

from typing import List, Optional

from laughtrack.core.clients.eventbrite.client import EventbriteClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from .extractor import EventbriteExtractor


class EventbriteScraper(BaseScraper):
    """
    Scraper for venues that use Eventbrite for event management.

    This scraper reads the club's eventbrite_id field and uses the
    EventbriteClient to fetch all events for that venue via API.
    """

    key = 'eventbrite'
    
    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)

        # Validate that club has eventbrite_id
        if not club.eventbrite_id:
            raise ValueError(f"Club {club.name} does not have an eventbrite_id configured")

        # Initialize the Eventbrite client
        self.eventbrite_client = EventbriteClient(club, proxy_pool=self.proxy_pool)

        self.logger_context = club.as_context()

    async def collect_scraping_targets(self) -> List[str]:
        """API-based: single logical target representing the venue ID."""
        return [self.club.eventbrite_id] if self.club.eventbrite_id else []

    async def get_data(self, target: str) -> Optional[EventListContainer]:
        """Fetch Eventbrite events and wrap into PageData container."""
        try:
            if not target:
                return None
            Logger.info(f"Fetching Eventbrite events for venue {target}", self.logger_context)
            events = await self.eventbrite_client.fetch_all_events()
            if not events:
                return None
            return EventbriteExtractor.to_page_data(events)
        except Exception as e:
            Logger.error(f"Error fetching Eventbrite data: {e}", self.logger_context)
            return None
