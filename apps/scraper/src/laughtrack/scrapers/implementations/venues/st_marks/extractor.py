"""
St. Marks event extractor for extracting Tixr URLs and event data.
"""

from typing import Dict, List, Optional

from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils


class StMarksEventExtractor:
    """Utility class for extracting St. Marks event data from HTML and Tixr URLs."""

    @staticmethod
    def extract_tixr_urls(html_content: str, logger_context: Optional[Dict] = None) -> List[str]:
        """
        Extract all Tixr URLs from the HTML content.

        Args:
            html_content: HTML content to parse
            logger_context: Logging context for error reporting

        Returns:
            List of Tixr URLs found in the page
        """
        try:
            # Reuse generic regex/pattern helper for hrefs
            urls = HtmlScraper.extract_links_by_regex_patterns(
                html=html_content,
                patterns=[r"https?://[^\s\"]*tixr\.com/[^\s\"]*/events/[^\s\"]*", r"/events/[^\s\"]*"],
            )

            # Keep only links that contain tixr.com and /events/
            filtered = [u for u in urls if "tixr.com" in u and "/events/" in u]

            # De-duplication already handled by helper; log and return
            Logger.info(f"Extracted {len(filtered)} unique Tixr URLs", logger_context or {})
            return filtered

        except Exception as e:
            Logger.error(f"Failed to extract Tixr URLs: {e}", logger_context or {})
            return []

    @staticmethod
    async def extract_tixr_event(
        tixr_url: str, tixr_client, logger_context: Optional[Dict] = None
    ) -> Optional[TixrEvent]:
        """
        Extract event details from a single Tixr URL using TixrClient.

        Args:
            tixr_url: Tixr event URL to process
            tixr_client: TixrClient instance for API calls
            logger_context: Logging context for error reporting

        Returns:
            TixrEvent object if successful, None otherwise
        """
        try:
            # Extract event ID from URL
            event_id = URLUtils.extract_id_from_url(tixr_url, ["/events/"])
            if not event_id:
                Logger.warn(f"Could not extract event ID from URL: {tixr_url}", logger_context or {})
                return None

            # Get event details from TixrClient
            show = await tixr_client.get_event_detail(event_id)
            if not show:
                Logger.warn(f"No show data returned for event ID: {event_id}", logger_context or {})
                return None

            # Create TixrEvent wrapper
            tixr_event = TixrEvent.from_tixr_show(show, tixr_url, event_id)
            return tixr_event

        except Exception as e:
            Logger.error(f"Error extracting Tixr event from {tixr_url}: {e}", logger_context or {})
            return None

    @staticmethod
    async def extract_events_from_urls(
        tixr_urls: List[str], tixr_client, logger_context: Optional[Dict] = None
    ) -> List[TixrEvent]:
        """
        Extract TixrEvent objects from multiple Tixr URLs.

        Args:
            tixr_urls: List of Tixr URLs to process
            tixr_client: TixrClient instance for API calls
            logger_context: Logging context for error reporting

        Returns:
            List of TixrEvent objects successfully created
        """
        tixr_events = []

        for tixr_url in tixr_urls:
            tixr_event = await StMarksEventExtractor.extract_tixr_event(tixr_url, tixr_client, logger_context)
            if tixr_event:
                tixr_events.append(tixr_event)

        Logger.info(
            f"Successfully extracted {len(tixr_events)} TixrEvents from {len(tixr_urls)} URLs", logger_context or {}
        )

        return tixr_events
