"""
Uncle Vinnie's Comedy Club event data model.

This model represents event data extracted from OvationTix API responses.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class UncleVinniesEvent:
    """
    Data model representing a single event from Uncle Vinnie's OvationTix API.
    """

    production_id: str
    performance_id: str
    name: str
    start_date: str
    description: Optional[str] = None
    sections: Optional[List[Dict[str, Any]]] = None
    ticket_types: Optional[List[Dict[str, Any]]] = None
    event_url: Optional[str] = None

    # Raw data preservation for debugging
    _raw_performance_data: Optional[JSONDict] = None

    def __post_init__(self):
        """Initialize empty lists if None provided."""
        if self.sections is None:
            self.sections = []
        if self.ticket_types is None:
            self.ticket_types = []

    def has_ticket_data(self) -> bool:
        """Check if this event has ticket information available."""
        return bool(self.sections or self.ticket_types)

    def get_ticket_count(self) -> int:
        """Get the total number of ticket types available."""
        total = 0
        if self.sections:
            for section in self.sections:
                ticket_type_views = section.get("ticketTypeViews", [])
                total += len(ticket_type_views)
        return total

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Transform UncleVinniesEvent object to Show objects with Uncle Vinnie's-specific processing."""
        try:
            # Parse datetime using factory utilities
            start_date = self._parse_event_datetime(club)
            if not start_date:
                Logger.error(f"Could not parse start date for event {self.name}: {self.start_date}")
                return None

            # Extract tickets from event data
            tickets = self._extract_tickets()

            # Create standardized show using factory
            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.name,
                club=club,
                date=start_date,
                show_page_url=self.event_url or "",
                lineup=[],  # Uncle Vinnie's doesn't provide structured lineup data
                tickets=tickets,
                description=self.description,
                room="",  # Uncle Vinnie's doesn't provide room information
                supplied_tags=["event"],
                enhanced=enhanced,
            )

        except Exception as e:
            Logger.error(f"Failed to transform UncleVinniesEvent data: {e}")
            return None

    def _parse_event_datetime(self, club: Club) -> Optional[datetime]:
        """
        Parse the event start date to a datetime object.

        Args:
            club: Club object containing timezone information

        Returns:
            Parsed datetime object or None if parsing fails
        """
        try:
            # Handle different date formats from OvationTix API
            if "T" in self.start_date and (
                "+" in self.start_date or self.start_date.endswith("Z") or self.start_date[-6] in "+-"
            ):
                # ISO 8601 format with timezone: "2025-06-28T20:00:00-04:00" or "2025-06-28T20:00:00Z"
                return ShowFactoryUtils.parse_datetime_with_timezone_fallback(self.start_date, club.timezone)

            elif "T" in self.start_date:
                # Format: "2025-07-09T20:00:00" (no timezone)
                local_tz = pytz.timezone(club.timezone)
                naive_datetime = datetime.strptime(self.start_date, "%Y-%m-%dT%H:%M:%S")
                return local_tz.localize(naive_datetime, is_dst=None)

            else:
                # Format: "2025-07-09 20:00" (no timezone)
                local_tz = pytz.timezone(club.timezone)
                naive_datetime = datetime.strptime(self.start_date, "%Y-%m-%d %H:%M")
                return local_tz.localize(naive_datetime, is_dst=None)

        except Exception as e:
            Logger.error(f"Error parsing start date {self.start_date}: {e}")
            return None

    def _extract_tickets(self) -> List[Ticket]:
        """
        Extract ticket information from UncleVinniesEvent.

        Args:
            event: UncleVinniesEvent object containing ticket data

        Returns:
            List of Ticket objects
        """
        tickets = []
        try:
            # Extract tickets from sections
            if self.sections:
                for section in self.sections:
                    ticket_type_views = section.get("ticketTypeViews", [])
                    for ticket_view in ticket_type_views:
                        price = ticket_view.get("price")
                        ticket_type = ticket_view.get("name", "General Admission")

                        if price is not None:
                            tickets.append(
                                Ticket(
                                    price=float(price),
                                    purchase_url=self.event_url or "",
                                    sold_out=False,
                                    type=ticket_type,
                                )
                            )

        except Exception as e:
            Logger.error(
                f"Failed to extract ticket data: {e}",
            )

        return tickets
