from typing import List, Optional

from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.exceptions import CircuitBreakerOpenError, NetworkError  # noqa: F401 — re-exported for callers
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.ports.scraping import EventListContainer
from .extractor import SeatEngineExtractor
from .transformer import SeatEngineEventTransformer


class SeatEngineScraper(BaseScraper):
    """
    Scraper for venues that use SeatEngine for event management.

    This scraper reads the club's seatengine_id field and uses the
    SeatEngineClient to fetch all events for that venue via API.
    """
    key = 'seatengine'
    
    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SeatEngineEventTransformer(club))

        # Validate that club has seatengine_id
        if not club.seatengine_id:
            raise ValueError(f"Club {club.name} does not have a seatengine_id configured")

        # Store the venue_id (seatengine_id)
        self.venue_id = club.seatengine_id

        # Initialize the SeatEngine client
        self.seatengine_client = SeatEngineClient(club, proxy_pool=self.proxy_pool)

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
                f"No events found for SeatEngine venue {self.club.seatengine_id}",
                self.logger_context,
            )
            return SeatEngineExtractor.to_page_data([])
        return SeatEngineExtractor.to_page_data(events_data)

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
            Logger.error(f"Club {self.club.name} missing seatengine_id", self.logger_context)
            return False

        return True
