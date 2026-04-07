"""
Uncle Vinnie's Comedy Club data extraction utilities.

Uses shared OvationTix extractor for common operations (production ID parsing,
past-event filtering) while keeping Uncle Vinnie's-specific logic for calendar
URL discovery and single-performance event creation.
"""

from typing import List, Optional

from laughtrack.core.clients.ovationtix.extractor import (
    extract_next_performance_info,
    is_past_event,
)
from laughtrack.core.entities.event.uncle_vinnies import UncleVinniesEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


class UncleVinniesExtractor:
    """Pure parsing utilities for Uncle Vinnie's responses."""

    @staticmethod
    def extract_event_urls_from_calendar_html(html: str, base_url: Optional[str] = None) -> List[str]:
        """Extract event URLs from a calendar page HTML."""
        try:
            return HtmlScraper.find_links_by_class(html, "tickets-button", base_url=base_url)
        except Exception as e:
            Logger.error(f"Error extracting event URLs: {e}")
            return []

    @staticmethod
    def extract_production_id(url: str) -> Optional[str]:
        """Extract the production ID from an OvationTix URL."""
        try:
            parts = url.split("/production/")
            if len(parts) != 2:
                return None
            production_id = parts[1].split("?")[0]
            return production_id or None
        except Exception as e:
            Logger.error(f"Failed to extract production ID from URL: {e}")
            return None

    @staticmethod
    def extract_next_performance_info(production_response: JSONDict) -> tuple[Optional[str], Optional[str]]:
        """From a Production(...)/performance? response, extract next performance id and start date."""
        return extract_next_performance_info(production_response)

    @staticmethod
    def create_event_from_performance_data(
        performance_data: JSONDict, production_id: str, event_url: str
    ) -> Optional[UncleVinniesEvent]:
        """Create an UncleVinniesEvent object from OvationTix performance data."""
        try:
            start_date = performance_data.get("startDate")
            production = performance_data.get("production", {}) or {}
            performance_id = performance_data.get("id", "")

            name = (
                production.get("productionName")
                or production.get("name")
                or production.get("supertitle")
                or "Comedy Show"
            )
            description = production.get("description")

            if not start_date or not isinstance(start_date, str) or not name:
                Logger.warn(
                    f"Missing required data for {event_url} - start_date: {start_date}, name: {name}"
                )
                return None

            sections = performance_data.get("sections", []) or production.get("sections", []) or []
            tickets_available = bool(performance_data.get("ticketsAvailable", True))

            return UncleVinniesEvent(
                production_id=production_id,
                performance_id=str(performance_id),
                production_name=name,
                start_date=start_date,
                description=description,
                sections=sections,
                ticket_types=[],
                event_url=event_url,
                tickets_available=tickets_available,
                _raw_performance_data=performance_data,
            )
        except Exception as e:
            Logger.error(f"Failed to create event from performance data: {e}")
            return None

    @staticmethod
    def is_past_event(start_date_str: str, timezone: str) -> bool:
        """Check if an event date string is in the past for a given timezone."""
        return is_past_event(start_date_str, timezone)
