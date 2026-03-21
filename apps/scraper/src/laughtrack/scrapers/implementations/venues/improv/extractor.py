"""
Extractor for Improv venue data.

Handles extraction of raw data from HTML content for improv.com venues.
Follows the standardized extractor pattern.
"""

import re
from typing import Dict, List, Optional

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.core.entities.event.improv import ImprovEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


class ImprovExtractor:
    """
    Extractor for Improv venue HTML content.

    Public Methods:
    - extract_event_urls(): Extract event URLs from calendar pages
    - extract_ticket_links(): Extract ticket purchase links from event pages
    - extract_ticket_offers(): Extract ticket offers with pricing data
    - extract_json_ld_events(): Extract JSON-LD event data
    - create_improv_event(): Create ImprovEvent from extracted data
    - process_ticket_url(): Complete ticket URL processing (main orchestrator)
    """

    @staticmethod
    def extract_event_urls(html: str, base_url: str, logger_context: Optional[Dict] = None) -> List[str]:
        """
        Extract event URLs from calendar page HTML.

        Args:
            html: HTML content from calendar page
            base_url: Base URL for constructing absolute URLs
            logger_context: Logging context for error reporting

        Returns:
            List of event URLs
        """
        try:
            # Use shared HTML scraper for event links
            event_urls = HtmlScraper.extract_links_by_text_pattern(
                html,
                "/event/",
                base_url=base_url,
                logger_context=logger_context,
            )

            Logger.info(f"Extracted {len(event_urls)} event URLs from calendar", logger_context)
            return event_urls

        except Exception as e:
            Logger.error(f"Failed to extract event URLs: {e}", logger_context)
            return []

    @staticmethod
    def extract_ticket_links(html: str, url: str, logger_context: Optional[Dict] = None) -> List[str]:
        """
        Extract ticket purchase links from button components with aria-labels.

        Looks for <a> tags within <div class="button"> that have aria-label attributes
        for buying tickets.

        Args:
            html: HTML content to parse
            url: Source URL for absolute link construction
            logger_context: Logging context for error reporting

        Returns:
            List of ticket purchase URLs
        """
        try:
            # New markup uses anchor elements whose class list contains "item"
            # Example: <a class="item showcase wtimes hasclubline" href="/addison/event/..." ...>
            links = HtmlScraper.find_links_by_class(html=html, class_name="item", base_url=url)
            Logger.info(f"Found {len(links)} ticket links", logger_context or {})
            return links

        except Exception as e:
            Logger.error(f"Failed to extract ticket links: {e}", logger_context or {})
            return []

    # _parse_single_offer removed in favor of HtmlScraper.extract_price_offers_from_containers

    @staticmethod
    def extract_json_ld_events(html: str, logger_context: Optional[Dict] = None) -> List[JsonLdEvent]:
        """
        Extract JSON-LD event data from HTML content.

        Args:
            html: HTML content to parse
            logger_context: Logging context for error reporting

        Returns:
            List of JsonLdEvent objects from JSON-LD data
        """
        try:
            return EventExtractor.extract_events(html)
        except Exception as e:
            Logger.error(f"Failed to extract JSON-LD events: {e}", logger_context or {})
            return []

    @staticmethod
    def create_improv_event(
        event_data, ticket_offers: List[dict], source_url: str = "", logger_context: Optional[Dict] = None
    ) -> Optional[ImprovEvent]:
        """
        Create an ImprovEvent from Event data and ticket offers.

        Args:
            event_data: Event object from JSON-LD extraction
            ticket_offers: List of ticket offer dictionaries with pricing info
            source_url: Original event page URL for context
            logger_context: Logging context for error reporting

        Returns:
            ImprovEvent instance or None if creation fails
        """
        try:
            # Extract basic event information from Event object
            name = event_data.name
            start_date = event_data.start_date
            event_url = event_data.url or source_url

            # Extract location information
            location_name = event_data.location.name if event_data.location else ""
            location_address = ""
            if event_data.location and event_data.location.address:
                location_address = event_data.location.address.street_address

            # Extract performer names
            performers = []
            if event_data.performers:
                performers = [performer.name for performer in event_data.performers]

            # Create debug data
            enriched_event_dict = {
                "name": name,
                "startDate": start_date.isoformat() if start_date else None,
                "url": event_url,
                "description": event_data.description,
                "location": {"name": location_name, "address": {"streetAddress": location_address}},
                "performers": [{"name": p} for p in performers],
                "_source_url": source_url,
                "_ticket_offers": ticket_offers,
            }

            return ImprovEvent(
                name=name,
                start_date=start_date,
                url=event_url,
                description=event_data.description or "",
                location_name=location_name,
                location_address=location_address,
                performers=performers,
                offers=ticket_offers,
                _raw_event_data=enriched_event_dict,
            )

        except Exception as e:
            Logger.error(f"Failed to create ImprovEvent: {e}", logger_context or {})
            return None

    @staticmethod
    def process_ticket_url(
        ticket_html: str, ticket_url: str, logger_context: Optional[Dict] = None
    ) -> Optional[List[ImprovEvent]]:
        try:
            # Step 1: Extract JSON-LD event data
            json_ld_events = ImprovExtractor.extract_json_ld_events(ticket_html, logger_context)
            if not json_ld_events:
                Logger.warning(f"No JSON-LD events found on ticket URL: {ticket_url}", logger_context or {})
                return None

            # Step 2: Convert each JsonLdEvent to ImprovEvent
            improv_events = []
            for event in json_ld_events:
                ticket_offers = [
                    {"url": offer.url, "price": offer.price, "name": offer.name or "General Admission"}
                    for offer in (event.offers or [])
                ]
                improv_events.append(
                    ImprovExtractor.create_improv_event(event, ticket_offers=ticket_offers, source_url=ticket_url, logger_context=logger_context)
                )
            improv_events = [e for e in improv_events if e is not None]

            if not improv_events:
                Logger.warning(f"No ImprovEvents created from ticket URL: {ticket_url}", logger_context or {})
                return None

            return improv_events

        except Exception as e:
            Logger.error(f"Error processing ticket URL {ticket_url}: {e}", logger_context or {})
            return None
