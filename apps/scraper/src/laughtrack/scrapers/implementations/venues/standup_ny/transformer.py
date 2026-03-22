"""
StandUp NY data transformer for converting StandupNYEvent objects to Show objects.

Handles the transformation of multi-source event data (GraphQL + VenuePilot) into
standardized Show objects for the Laughtrack database.
"""

from typing import Any, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.event.standup_ny import StandupNYEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.foundation.utilities.datetime import DateTimeUtils


class StandupNYEventTransformer(DataTransformer[StandupNYEvent]):
    """
    Transform StandUp NY combined event data into Show objects.

    This transformer handles the complex data merging from:
    - GraphQL API event data (ShowTix4U/VenuePilot)
    - Enhanced VenuePilot ticket page data
    """

    def __init__(self, club: Club):
        self.club = club
        self.logger_context = {"club": club.name, "transformer": "standup_ny"}

    def transform_to_show(self, event: StandupNYEvent) -> Optional[Show]:
        """Transform a single StandupNYEvent to a Show (pipeline interface)."""
        return self._transform_single_event(event, "")

    def _transform_single_event(self, event: StandupNYEvent, source_url: str) -> Optional[Show]:
        """
        Transform a single StandupNYEvent to Show object.

        Args:
            event: StandupNYEvent to transform
            source_url: Original source URL

        Returns:
            Show object or None if transformation failed
        """
        try:
            # Get the effective values from the event (prefers VenuePilot data)
            name = event.get_effective_name()
            if not name:
                Logger.warn(f"Event {event.id} missing name", self.logger_context)
                return None

            # Parse the event datetime
            formatted_datetime = self._parse_event_datetime(event)
            if not formatted_datetime:
                Logger.warn(f"Event {event.id} missing valid datetime", self.logger_context)
                return None

            # Get effective description and ticket URL
            description = event.get_effective_description()
            show_page_url = event.get_effective_ticket_url()

            # Extract ticket information
            tickets = self._extract_tickets(event)

            # Extract comedian lineup
            lineup = self._extract_lineup(event)

            # Create Show using the factory method
            return Show.create(
                name=name,
                date=formatted_datetime,
                description=description,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                supplied_tags=["event"],  # Default tags for StandUp NY events
                timezone=None,  # DateTimeUtils handles timezone conversion
                club_id=self.club.id,
                room="",  # Room info not available in current data sources
            )

        except Exception as e:
            Logger.error(f"Error creating show from event {event.id}: {e}", self.logger_context)
            return None

    def _parse_event_datetime(self, event: StandupNYEvent) -> Optional[Any]:
        """
        Parse the event datetime from multi-source data.

        Args:
            event: StandupNYEvent with datetime information

        Returns:
            Parsed datetime object or None if parsing failed
        """
        try:
            # Check for VenuePilot enhanced start time first
            if event.venue_pilot_event and event.venue_pilot_event.get("startTime"):
                date_str = event.venue_pilot_event["startTime"]
            else:
                date_str = event.start_time

            if not date_str:
                return None

            # Handle time-only strings by combining with event date
            if ":" in date_str and len(date_str) <= 8:  # Time-only format like "18:00:00"
                if event.date:
                    # Combine date and time
                    combined_datetime = f"{event.date}T{date_str}"
                    return DateTimeUtils.parse_datetime_with_timezone(combined_datetime, self.club.timezone)
                else:
                    Logger.warn(
                        f"Time-only string {date_str} found but no date available for event {event.id}",
                        self.logger_context,
                    )
                    return None
            else:
                # Full datetime string
                return DateTimeUtils.parse_datetime_with_timezone(date_str, self.club.timezone)

        except Exception as e:
            Logger.warn(f"Error parsing date for event {event.id}: {e}", self.logger_context)
            return None

    def _extract_lineup(self, event: StandupNYEvent) -> List[Comedian]:
        """
        Extract comedian lineup from StandupNYEvent.

        Uses VenuePilot performer data when available, falls back to GraphQL
        promoter/support fields.
        """
        lineup = []
        for name in event.get_lineup_names():
            lineup.append(Comedian(name=name))
        return lineup

    def _extract_tickets(self, event: StandupNYEvent) -> List[Ticket]:
        """
        Extract ticket information from StandupNYEvent.

        Args:
            event: StandupNYEvent with ticket data

        Returns:
            List of Ticket objects
        """
        tickets = []

        try:
            # Check for enhanced VenuePilot ticket data first
            if event.has_enhanced_ticket_data():
                tickets = self._extract_venue_pilot_tickets(event)

            # Fallback to basic ticket from GraphQL data
            if not tickets and event.ticket_url:
                tickets = [
                    Ticket(
                        price=0.0,  # Price unknown from GraphQL API
                        purchase_url=event.get_effective_ticket_url(),
                        sold_out=False,
                        type="General Admission",
                    )
                ]

            return tickets

        except Exception as e:
            Logger.error(f"Error extracting tickets for event {event.id}: {e}", self.logger_context)
            return []

    def _extract_venue_pilot_tickets(self, event: StandupNYEvent) -> List[Ticket]:
        """
        Extract detailed ticket information from VenuePilot data.

        Args:
            event: StandupNYEvent with VenuePilot ticket data

        Returns:
            List of Ticket objects from VenuePilot data
        """
        tickets = []

        try:
            if not event.venue_pilot_tickets:
                return tickets

            ticket_url = event.get_effective_ticket_url()

            for ticket_data in event.venue_pilot_tickets:
                breakdown = ticket_data.get("breakdown", {})
                price = breakdown.get("price", 0.0)

                ticket = Ticket(
                    price=float(price) if price else 0.0,
                    purchase_url=ticket_url,
                    sold_out=ticket_data.get("soldOut", False),
                    type=ticket_data.get("type", "General Admission"),
                )
                tickets.append(ticket)

            return tickets

        except Exception as e:
            Logger.error(f"Error extracting VenuePilot tickets for event {event.id}: {e}", self.logger_context)
            return []
