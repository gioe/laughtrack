"""
The Stand NYC specialized scraper implementation using standardized project patterns.

This scraper handles thestandnyc.com's unique structure:
1. Event pages contain Tixr links rather than JSON-LD data
2. Dual pagination: date-based (monthly calendar) and horizontal ("More Shows")
3. Tixr URLs need to be extracted and passed to TixrClient for event details

Clean single-responsibility architecture:
- TheStandEventExtractor: HTML → Tixr URL extraction
- TheStandEventTransformer: TixrEvent objects → Show objects
- TheStandNYCScraper: Orchestrates extraction and transformation with complex pagination
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.infrastructure.monitoring import create_monitored_tixr_client
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper
from laughtrack.foundation.utilities.url import URLUtils

from .extractor import TheStandEventExtractor
from .page_data import TheStandPageData
from .transformer import TheStandEventTransformer


class TheStandNYCScraper(BaseScraper):
    """
    Specialized scraper for The Stand NYC using standardized project patterns.

    This implementation:
    1. Uses BaseScraper's standard pipeline (discover_urls → extract_data → transform_data)
    2. Leverages built-in fetch methods with error handling and retries
    3. Implements complex dual pagination specific to The Stand
    4. Uses TixrClient for external API integration
    5. Separates concerns: URL extraction vs Tixr event processing
    """

    key = "the_stand_nyc"

    def __init__(self, club: Club):
        super().__init__(club)
        # Initialize TixrClient with monitoring integration (if available)
        self.tixr_client = create_monitored_tixr_client(club)

        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_comedy_venue_config(),
            logger_context=club.as_context(),
        )

    async def discover_urls(self) -> List[str]:
        """
        Discover URLs to scrape using complex dual pagination.

        The Stand has dual pagination:
        1. Horizontal pagination: "More Shows" button (exhausted first for each month)
        2. Date-based pagination: Monthly calendar navigation (6 months total)

        Returns all URLs found through pagination.
        """
        all_urls = []
        # Handle URLs from database - just add protocol if missing
        start_url = self.club.scraping_url
        if not start_url.startswith(("http://", "https://")):
            start_url = f"https://{start_url}"

        try:
            months_processed = 0
            max_months = 6
            current_month_url = start_url

            while months_processed < max_months and current_month_url:
                months_processed += 1

                # Step 1: Exhaust horizontal pagination ("More Shows") for this month
                month_urls = await self._discover_month_horizontal_urls(current_month_url)
                all_urls.extend(month_urls)

                # Step 2: Get next month URL using date pagination
                current_month_url = await self._get_next_month_url(current_month_url)
                if not current_month_url:
                    break

            Logger.info(
                f"Discovered {len(all_urls)} URLs across {months_processed} months",
                self.logger_context,
            )
            return all_urls

        except Exception as e:
            Logger.error(f"URL discovery failed: {e}", self.logger_context)
            return [start_url]  # Fallback to just the start URL

    async def _discover_month_horizontal_urls(self, start_url: str) -> List[str]:
        """
        Discover all URLs for a single month using horizontal pagination ("More Shows").

        Args:
            start_url: URL for the month to discover URLs from

        Returns:
            List of URLs found in this month
        """
        month_urls = [start_url]
        current_url = start_url
        page_count = 0

        while current_url:
            page_count += 1
            try:
                # Fetch the page
                html_content = await self.fetch_html(URLUtils.normalize_url(current_url))

                # Look for "More Shows" link to continue horizontal pagination
                next_url = TheStandEventExtractor.extract_pagination_url(html_content, current_url)
                if next_url and next_url not in month_urls:
                    month_urls.append(next_url)
                    current_url = next_url
                else:
                    break

            except Exception as e:
                Logger.error(f"Error processing horizontal page: {e}", self.logger_context)
                break

        Logger.info(f"Found {len(month_urls)} URLs in month via horizontal pagination", self.logger_context)
        return month_urls

    async def _get_next_month_url(self, current_url: str) -> Optional[str]:
        """
        Get the URL for the next month using date-based pagination.

        Args:
            current_url: Current month URL

        Returns:
            Next month URL if found, None otherwise
        """
        try:
            html_content = await self.fetch_html(URLUtils.normalize_url(current_url))
            next_url = TheStandEventExtractor.extract_pagination_url(html_content, current_url)

            # Only consider it a "next month" if it's different from horizontal pagination
            # This is a simplified check - in practice, we'd need more sophisticated logic
            return next_url if next_url else None

        except Exception as e:
            Logger.error(f"Error finding next month URL from {current_url}: {e}", self.logger_context)
            return None

    async def get_data(self, url: str) -> Optional[TheStandPageData]:
        """
        Extract Tixr URLs from The Stand NYC webpage.

        Args:
            url: The Stand NYC page URL to extract from

        Returns:
            TheStandPageData containing Tixr URLs found on the page
        """
        try:
            # Use BaseScraper's standardized fetch_html with built-in error handling
            html_content = await self.fetch_html(URLUtils.normalize_url(url))

            # Extract Tixr URLs from the HTML
            tixr_urls = TheStandEventExtractor.extract_tixr_urls(html_content)

            if not tixr_urls:
                Logger.info(f"No Tixr URLs found on {url}", self.logger_context)
                return None

            Logger.info(f"Extracted {len(tixr_urls)} Tixr URLs from {url}", self.logger_context)
            return TheStandPageData(tixr_urls=tixr_urls)

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {str(e)}", self.logger_context)
            return None
