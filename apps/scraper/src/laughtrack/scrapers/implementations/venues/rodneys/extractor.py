"""Rodney's Comedy Club data extraction utilities."""

from typing import List, Optional

from laughtrack.core.entities.event.rodneys import RodneyEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


class RodneyEventExtractor:
    """Utility class for extracting Rodney's Comedy Club event data from various sources."""

    @staticmethod
    def extract_show_links(html_content: str) -> List[str]:
        """
        Extract show page links from the main Rodney's page HTML.

        Args:
            html_content: HTML content from main page

        Returns:
            List of show page URLs
        """
        try:
            # Extract all links whose href starts with the shows path
            links = HtmlScraper.extract_links_by_text_pattern(
                html_content, "rodneysnewyorkcomedyclub.com/shows"
            )
            # Deduplicate while preserving order
            seen: set = set()
            show_links = []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    show_links.append(link)
            return show_links
        except Exception as e:
            Logger.error(f"Failed to extract show links: {e}")
            return []

    @staticmethod
    def extract_events_from_html(html_content: str, source_url: str) -> List[RodneyEvent]:
        """
        Extract Rodney events from direct HTML pages using JSON-LD.

        Args:
            html_content: HTML content from show page
            source_url: URL where the data was extracted from
            logger_context: Logging context for error reporting

        Returns:
            List of RodneyEvent objects extracted from JSON-LD
        """
        try:
            # Extract JSON-LD data using shared extractor
            events = EventExtractor.extract_events(html_content)

            if not events:
                return []

            # Convert Event objects to RodneyEvent objects
            rodney_events = []
            for event in events:
                try:
                    rodney_event = RodneyEvent.from_html_event(event, source_url)
                    rodney_events.append(rodney_event)
                except Exception as e:
                    Logger.warn(f"Failed to convert Event to RodneyEvent: {e}")
                    continue

            return rodney_events

        except Exception as e:
            Logger.error(f"Failed to extract events from HTML: {e}")
            return []

    @staticmethod
    def extract_event_from_json_ld(html_content: str, source_url: str) -> Optional[RodneyEvent]:
        """
        Extract RodneyEvent from JSON-LD script tags in HTML.

        Args:
            html_content: HTML content containing JSON-LD script tags
            source_url: URL where the data was extracted from

        Returns:
            RodneyEvent object if successfully extracted, None otherwise
        """
        try:
            # Use the existing EventExtractor to get Event objects from JSON-LD
            events = EventExtractor.extract_events(html_content)

            if not events:
                Logger.warn(f"No events found in JSON-LD from {source_url}")
                return None

            # Convert the first Event to RodneyEvent
            event = events[0]  # Take the first event found
            rodney_event = RodneyEvent.from_html_event(event, source_url)
            return rodney_event

        except Exception as e:
            Logger.error(f"Failed to extract event from JSON-LD: {e}")
            return None
