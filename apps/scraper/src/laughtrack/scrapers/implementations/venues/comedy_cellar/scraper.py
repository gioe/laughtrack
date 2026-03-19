"""
Refactored Comedy Cellar scraper implementation using the new BaseScraper two-phase architecture.

This implementation leverages the optimized BaseScraper pipeline:
- Phase 1: Concurrent async data fetching from Comedy Cellar's APIs
- Phase 2: Sync transformation using the standard transformation pipeline
- ComedyCellarExtractor: Handles data mapping from API responses
- Standard transformation pipeline: Transforms page data to Show objects

Clean single-responsibility architecture optimized for performance:
- ComedyCellarScraper: Handles async network requests and session management
- ComedyCellarExtractor: API response mapping → ComedyCellarDateData objects
- Standard pipeline: ComedyCellarDateData objects → Show objects via transformation pipeline
"""

import asyncio
from typing import List, Optional

from laughtrack.core.clients.comedy_cellar.client import ComedyCellarAPIClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.scrapers.base.base_scraper import BaseScraper
# Client ensures Comedy Cellar API response validity and raises on errors

from .data import ComedyCellarDateData
from .extractor import ComedyCellarExtractor
from .transformer import ComedyCellarEventTransformer


class ComedyCellarScraper(BaseScraper):
    """
    Refactored Comedy Cellar scraper using the new BaseScraper two-phase architecture.

    This implementation leverages the optimized BaseScraper pipeline:
    1. Phase 1: Concurrent async data fetching from multiple date targets
    2. Phase 2: Sync transformation using the standard transformation pipeline
    3. Uses ComedyCellarExtractor for data mapping from API responses
    4. Uses standard transformation pipeline for converting to Show objects
    5. Follows established error handling and logging patterns
    6. Separates concerns: async I/O vs sync CPU work for optimal performance

    The scraper now benefits from:
    - Concurrent fetching of all date targets (no blocking on transformation)
    - Better async event loop utilization
    - Standardized transformation pipeline integration
    """

    key = "comedy_cellar"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ComedyCellarEventTransformer(club))
        self.api_client = ComedyCellarAPIClient(club, proxy_pool=self.proxy_pool)

    async def collect_scraping_targets(self) -> List[str]:
        """
        Discover available dates to scrape from Comedy Cellar's API.

        This method implements the target discovery phase of the BaseScraper pipeline.
        For Comedy Cellar, targets are date strings that will be used to make API calls.

        Returns:
            List of date strings that can be processed by get_data()
        """
        return await self.api_client.discover_available_dates()

    async def get_data(self, target: ScrapingTarget) -> Optional[ComedyCellarDateData]:
        """
        Extract Comedy Cellar data for a specific date using concurrent API calls.

        This method implements the data extraction phase of the new BaseScraper pipeline.
        It makes parallel API requests and combines the data into a standardized format
        that implements the EventListContainer protocol.

        The method is optimized for the two-phase architecture:
        - Focuses purely on async I/O (API calls)
        - No transformation work (handled in Phase 2)
        - Returns EventListContainer for standard pipeline processing

        Args:
            target: Date string to extract data for (e.g., "2024-01-15")

        Returns:
            ComedyCellarDateData object implementing EventListContainer protocol,
            or None if extraction failed
        """
        try:
            # Make two parallel requests for this date using the client
            lineup_task = self.api_client.get_lineup_data(target)
            shows_task = self.api_client.get_shows_data(target)

            # Let exceptions propagate; client raises on invalid responses
            processed_lineup_data, processed_shows_data = await asyncio.gather(lineup_task, shows_task)

            # Use extractor to combine the data into EventListContainer format
            event_list = ComedyCellarExtractor.extract_events(target, processed_lineup_data, processed_shows_data)
            
            if not event_list:
                Logger.info("No events found on page", self.logger_context)
                return None
            return ComedyCellarDateData(event_list)

        except Exception as e:
            Logger.error(f"Error extracting data for {target}: {str(e)}", self.logger_context)
            return None
