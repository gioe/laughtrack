"""
Uncle Vinnie's Comedy Club data extraction utilities.

This extractor now focuses solely on parsing and model creation. All HTTP
requests and workflow orchestration are handled by the Scraper using the
BaseScraper HTTP utilities.
"""

from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.event.uncle_vinnies import UncleVinniesEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


class UncleVinniesExtractor:
    """Pure parsing utilities for Uncle Vinnie's responses."""

    @staticmethod
    def extract_event_urls_from_calendar_html(html: str, base_url: Optional[str] = None) -> List[str]:
        """
        Extract event URLs from a calendar page HTML.

        Args:
            html: HTML content of the calendar page
            base_url: Optional base URL to construct absolute URLs

        Returns:
            List of event URLs
        """
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
        """
        From a Production(...)/performance? response, extract next performance id and start date.

        Returns: (performance_id, start_date_str)
        """
        try:
            performance_summary = production_response.get("performanceSummary", {}) or {}
            next_performance = performance_summary.get("nextPerformance", {}) or {}
            return next_performance.get("id"), next_performance.get("startDate")
        except Exception:
            return None, None

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
                name=name,
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
        try:
            # Try multiple formats commonly returned by OvationTix
            dt: Optional[datetime] = None
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(start_date_str, fmt)
                    break
                except Exception:
                    continue

            if dt is None:
                # As a conservative default, don't filter out events we can't parse
                return False

            tz = pytz.timezone(timezone)
            event_dt = tz.localize(dt)
            now = datetime.now(tz)
            return event_dt < now
        except Exception:
            return False
