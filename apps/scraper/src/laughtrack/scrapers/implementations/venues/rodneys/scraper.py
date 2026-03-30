"""
Rodney's Comedy Club scraper implementation.

This scraper follows the 5-component architecture pattern and handles multiple data sources:
1. Scrape the main page for show page links
2. Scrape individual show pages for event details
3. Handle redirects to external ticketing platforms (Eventbrite, 22Rams)

Architecture Components:
- RodneysComedyClubScraper: Main orchestration class
- RodneyEventExtractor: Data extraction from multiple sources
- RodneyEventTransformer: Data transformation to Show objects
- RodneyPageData: Data model for extracted data
- RodneyEvent: Domain model for venue-specific event data
"""

from dataclasses import asdict
from typing import List, Optional

from laughtrack.core.entities.event.eventbrite import EventbriteEvent as DomainEventbriteEvent
from laughtrack.core.entities.event.rodneys import RodneyEvent
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper
from laughtrack.foundation.utilities.url import URLUtils

from .data import RodneyPageData
from .extractor import RodneyEventExtractor
from .transformer import RodneyEventTransformer


class RodneysComedyClubScraper(BaseScraper):
    """
    Rodney's Comedy Club scraper following the 5-component architecture.

    This scraper handles multiple data sources:
    - Direct HTML pages with JSON-LD structured data
    - Eventbrite API redirects
    - 22Rams API redirects

    Follows the standardized pipeline:
    discover_urls() → extract_data() → transform_data() → scrape_async()
    """

    key = "rodneys"

    def __init__(self, club: Club, **kwargs):
        """Initialize the scraper with club information."""
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(RodneyEventTransformer(club))

        # Headers for scraping - using BaseHeaders for consistency
        self.headers = BaseHeaders.get_headers(
            base_type="rodneys", host="rodneysnewyorkcomedyclub.com"
        )

    async def discover_urls(self) -> List[str]:
        """
        Discover event URLs by scraping the main page for show links.

        Returns:
            List of individual show page URLs to process
        """
        try:
            # Normalize the scraping URL to ensure it has protocol
            normalized_url = URLUtils.normalize_url(self.club.scraping_url)

            # Fetch HTML using built-in method
            html_content = await self.fetch_html(normalized_url)

            if not html_content:
                return []

            # Extract show links using extractor
            links = RodneyEventExtractor.extract_show_links(html_content)

            Logger.info(f"{self._log_prefix}: Discovered {len(links)} show URLs", self.logger_context)
            return links

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error discovering URLs: {e}", self.logger_context)
            return []

    async def get_data(self, url: str) -> Optional[RodneyPageData]:
        """
        Extract raw data from a show page URL.

        Determines the appropriate method based on the URL domain:
        - eventbrite.com: Use EventbriteClient
        - 22rams.com: Use TwentyTwoRamsClient
        - Other domains: Direct HTTP request with JSON-LD extraction

        Args:
            url: The show page URL

        Returns:
            RodneyPageData containing list of RodneyEvent objects
        """
        try:

            # Normalize the passed-in show page URL (not the calendar listing URL)
            normalized_url = URLUtils.normalize_url(url)

            # Fetch HTML using built-in method
            html_content = await self.fetch_html(normalized_url)

            event_list = RodneyEventExtractor.extract_events_from_html(html_content, url)

            return RodneyPageData(event_list=event_list)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {e}", self.logger_context)
            return None
