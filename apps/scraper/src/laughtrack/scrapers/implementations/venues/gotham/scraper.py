"""
Gotham Comedy Club scraper implementation using standardized project patterns.

This scraper handles Gotham Comedy Club's S3 bucket-based event system that provides
a JSON API endpoint with event data. The scraper fetches the events JSON and transforms
the data into Show objects.

This implementation follows the established architectural patterns:
- BaseScraper pipeline for standard workflow
- GothamEventExtractor: Handles S3 JSON data extraction and enrichment
- GothamEventTransformer: Transforms GothamEvent objects to Show objects
- GothamPageData: Data model for extracted page data

Clean single-responsibility architecture:
- GothamEventExtractor: S3 JSON API → GothamEvent objects with enrichment
- GothamEventTransformer: GothamEvent objects → Show objects
- GothamComedyClubScraper: Orchestrates the standard pipeline
"""

from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import GothamEventExtractor


class GothamComedyClubScraper(BaseScraper):
    """
    Gotham Comedy Club scraper using standardized project patterns.

    This implementation:
    1. Uses BaseScraper's standard pipeline (collect_scraping_targets → get_data → transform_data)
    2. Leverages built-in fetch methods with error handling and retries
    3. Follows established error handling and logging patterns
    4. Separates concerns: extraction vs transformation via dedicated classes
    """

    key = "gotham"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.extractor = GothamEventExtractor(club, self.get_session, proxy_pool=self.proxy_pool)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Generate monthly JSON URLs for the next 10 months starting from current month.

        Returns:
            List of monthly S3 JSON endpoint URLs
        """
        base_url = "https://gothamevents.s3.amazonaws.com/events/month/"
        targets = self._generate_monthly_urls(base_url, num_months=10)

        Logger.info(
            f"Generated {len(targets)} monthly URLs for Gotham Comedy Club",
            self.logger_context,
        )

        return targets

    def _generate_monthly_urls(self, base_url: str, num_months: int = 10) -> List[str]:
        """
        Generate monthly JSON URLs for the specified number of months.

        Args:
            base_url: The base S3 bucket URL
            num_months: Number of months to generate URLs for

        Returns:
            List of monthly JSON endpoint URLs
        """
        urls = []
        current_date = datetime.now()

        for i in range(num_months):
            # Calculate the target month by properly incrementing months
            year = current_date.year
            month = current_date.month + i

            # Handle year rollover
            while month > 12:
                month -= 12
                year += 1

            month_str = f"{year:04d}-{month:02d}"
            monthly_url = f"{base_url}{month_str}.json"
            urls.append(monthly_url)

        return urls

    async def get_data(self, target: ScrapingTarget) -> Optional[EventListContainer]:
        """
        Extract Gotham event data from S3 JSON using the dedicated extractor.

        For S3 URLs, 403/404 responses are expected for future months without events.

        Args:
            target: A monthly JSON file URL (e.g., .../2025-07.json)

        Returns:
            GothamPageData containing the events data or None if failed
        """
        return await self.extractor.extract_events(target)
