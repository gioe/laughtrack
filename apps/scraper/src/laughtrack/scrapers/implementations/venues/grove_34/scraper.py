"""
Grove34 specialized scraper.

This scraper handles grove34.com's unique structure where:
1. Events are embedded in <script type="application/json" id="wix-warmup-data">
2. Event data is nested under appsWarmupData -> widget ID -> events.events
3. Uses Wix Events platform with structured event data

Follows the standard 5-component architecture pattern for External API Integration (Pattern D).
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils

from .data import Grove34PageData
from .extractor import Grove34EventExtractor


class Grove34Scraper(BaseScraper):
    """
    Specialized scraper for grove34.com.

    Handles grove34.com's unique Wix Events platform structure.
    Extracts event data from Wix warmup data embedded in script tag.
    Events contain comprehensive information including tickets, pricing, and scheduling.

    Follows Pattern D: External API Integration from scraper architecture patterns.
    """

    key = "grove34"

    def __init__(self, club: Club):
        super().__init__(club)

    async def get_data(self, url: str) -> Optional[Grove34PageData]:
        """
        Extract raw data from Grove34's warmup data using standardized methods.

        Args:
            url: URL to extract data from

        Returns:
            Grove34PageData containing extracted Grove34Event objects or None if extraction failed
        """
        try:
            # Use BaseScraper's standardized fetch_html with built-in error handling
            url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(url)

            # Extract Grove34 events using the extractor
            event_list = Grove34EventExtractor.extract_events(html_content)

            if not event_list:
                Logger.warning(f"No events found in warmup data from {url}", self.logger_context)
                return None

            return Grove34PageData(event_list)

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {e}", self.logger_context)
            return None
