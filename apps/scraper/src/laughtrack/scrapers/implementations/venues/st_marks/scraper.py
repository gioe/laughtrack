"""
StMarks specialized scraper following the 5-component architecture.

This scraper handles St. Marks venues that contain Tixr links.
The workflow follows the standard pipeline:
1. discover_urls() → [club.scraping_url]
2. extract_data() → Extract Tixr URLs and convert to TixrEvents
3. transform_data() → Convert TixrEvents to Show objects

Architecture Components:
- StMarksScraper: Main orchestration class
- StMarksEventExtractor: Data extraction from HTML and Tixr URLs
- StMarksEventTransformer: Data transformation to Show objects
- StMarksPageData: Data model for extracted data
- TixrEvent: Domain model for Tixr-specific event data
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.infrastructure.monitoring import create_monitored_tixr_client
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.utilities.infrastructure.scraper import log_filter_breakdown

from .data import StMarksPageData
from .extractor import StMarksEventExtractor
from .transformer import StMarksEventTransformer


class StMarksScraper(BaseScraper):
    """
    Specialized scraper for St. Marks venues following the 5-component architecture.

    This scraper extracts Tixr event URLs from HTML pages and uses TixrClient
    to fetch event details, following the standardized pipeline:
    discover_urls() → extract_data() → transform_data() → scrape_async()
    """

    key = "st_marks"

    def __init__(self, club: Club, **kwargs):
        """Initialize the scraper with club information."""
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(StMarksEventTransformer(club))

        # Initialize TixrClient with monitoring integration (if available)
        self.tixr_client = create_monitored_tixr_client(club)

        # Initialize batch scraper with comedy venue configuration
        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_comedy_venue_config(), logger_context={"club": club.name, "scraper": self.key}
        )

    async def get_data(self, url: str) -> Optional[StMarksPageData]:
        """
        Extract TixrEvent data from a URL.

        For St. Marks, this extracts Tixr URLs from the HTML page,
        then uses TixrClient to get event details for each URL.

        Args:
            url: The URL to extract data from (should be club.scraping_url)

        Returns:
            StMarksPageData containing extracted TixrEvent objects, or None if failed
        """
        try:
            # Normalize the URL
            normalized_url = URLUtils.normalize_url(url)

            # Fetch HTML via TixrClient's headerless method — DataDome blocks requests
            # that carry application-level headers (Accept-Language + Cache-Control +
            # Pragma together); curl_cffi impersonation alone avoids the 403.
            html_content = await self.tixr_client._fetch_tixr_page(normalized_url)
            if not html_content:
                Logger.warn(f"{self.__class__.__name__} [{self._club.name}]: No HTML content found at {normalized_url}", self.logger_context)
                return None

            # Extract Tixr URLs from the HTML
            tixr_urls = StMarksEventExtractor.extract_tixr_urls(html_content, self.logger_context)
            if not tixr_urls:
                Logger.warn(f"{self.__class__.__name__} [{self._club.name}]: No Tixr URLs found at {normalized_url}", self.logger_context)
                return None

            Logger.info(f"{self.__class__.__name__} [{self._club.name}]: Found {len(tixr_urls)} Tixr URLs to process", self.logger_context)

            # Diagnostics: log which URLs appear to contain Tixr event IDs before enrichment/API calls
            log_filter_breakdown(
                tixr_urls,
                self.logger_context,
                id_getter=lambda u: URLUtils.extract_id_from_url(u, ["/events/"]),
                accept_predicate=lambda u: bool(URLUtils.extract_id_from_url(u, ["/events/"])),
                label="Tixr URL enrichment",
                name_getter=lambda u: u,
                date_getter=None,
            )

            # Process Tixr URLs using batch processing for performance
            results = await self.batch_scraper.process_batch(
                tixr_urls, lambda url: self.tixr_client.get_event_detail_from_url(url), "Tixr event extraction"
            )

            # Filter out None results
            tixr_events = [result for result in results if result is not None]

            Logger.info(
                f"{self.__class__.__name__} [{self._club.name}]: Successfully processed {len(tixr_events)} TixrEvents from {len(tixr_urls)} URLs", self.logger_context
            )

            return StMarksPageData(event_list=tixr_events, source_url=normalized_url)

        except Exception as e:
            Logger.error(f"{self.__class__.__name__} [{self._club.name}]: Error extracting data from {url}: {e}", self.logger_context)
            return None
