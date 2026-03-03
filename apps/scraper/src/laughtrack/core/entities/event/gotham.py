from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from laughtrack.core.clients.showclix.models import ShowclixEventData
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.local.gotham_show import GothamShow
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils


@dataclass
class GothamEvent:
    """
    Data model representing a single event from Gotham Comedy Club's S3 JSON API.

    This corresponds to the JSON structure returned by their monthly event endpoints.
    Each event can have multiple shows at different times.
    """

    id: str
    name: str
    date: str
    hours: int
    minutes: int
    slug: Optional[str] = None
    shows: Optional[List[GothamShow]] = None

    # Raw event data for reference
    _raw_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.shows is None:
            self.shows = []

    def to_show(self, club: Club) -> Optional[Show]:
        """Factory method to create a Show from a GothamEvent and Club.

        Args:
            event_data: The GothamEvent instance to convert
            club: The Club instance for the show

        Returns:
            Show: A new Show instance created from the GothamEvent, or None if transformation failed
        """
        try:
            # Basic validation
            if not self.name:
                Logger.warn("Event missing name field")
                return None

            # Parse the event date and time
            if not self.date:
                Logger.warn(f"Event {self.name} missing date field")
                return None

            # Parse datetime - combine date with time
            try:
                base_date = DateTimeUtils.parse_datetime_with_timezone(self.date, "America/New_York")
                date = base_date.replace(hour=self.hours, minute=self.minutes)
            except Exception as e:
                Logger.warn(f"Failed to parse date {self.date} for event {self.name}: {e}")
                return None

            # Extract show page URL from shows array
            show_page_url = self._extract_show_page_url()

            # Extract room information from the name
            room_patterns = {"vintage lounge": "The Vintage Lounge"}
            room = ShowFactoryUtils.extract_room_from_name(self.name, room_patterns) or "Main Room"

            # Extract ticket information from shows array
            tickets = self._extract_tickets(show_page_url)

            # Build description
            description = f"Comedy show: {self.name}"

            # Create standardized show (Gotham events don't support enhanced processing currently)
            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.name,
                club=club,
                date=date,
                show_page_url=show_page_url,
                lineup=[],  # No comedian lineup info in API response
                tickets=tickets,
                description=description,
                room=room,
                supplied_tags=["event"],
                enhanced=False,  # Gotham events use basic processing
            )

        except Exception as e:
            Logger.error(f"Error transforming event data: {e}")
            return None

    def _extract_show_page_url(self) -> str:
        """
        Extract show page URL from the event data.

        Args:
            event_data: GothamEvent object

        Returns:
            Show page URL
        """
        shows = self.shows or []

        # Try to get listing URL from shows array
        if shows and len(shows) > 0:
            show_page_url = shows[0].listing_url
            if show_page_url:
                return show_page_url

        # Fallback to a constructed URL if listing-url is missing
        slug = self.slug or "unknown"
        return f"https://www.showclix.com/event/{slug}"

    def _extract_tickets(self, listing_url: Optional[str]) -> List[Ticket]:
        """
        Extract ticket information from shows array.

        Args:
            shows: List of GothamShow objects from the event

        Returns:
            List of Ticket objects
        """
        tickets = []

        try:
            if listing_url:
                # Create a basic ticket with the listing URL
                tickets.append(ShowFactoryUtils.create_fallback_ticket(listing_url))

        except Exception as e:
            Logger.warn(f"Error extracting ticket information: {e}")

        return tickets

    def enrich_with_showclix_data(self, event_data: ShowclixEventData) -> "GothamEvent":
        """
        Enrich this GothamEvent with ticket data from Showclix API.

        Args:
            event_data: ShowclixEventData from API

        Returns:
            New enriched GothamEvent with updated ticket data
        """
        try:
            # Create a copy of the event to avoid modifying the original
            enriched_event = GothamEvent(
                id=self.id,
                name=self.name,
                date=self.date,
                hours=self.hours,
                minutes=self.minutes,
                slug=self.slug,
                shows=self.shows.copy() if self.shows else [],
                _raw_data=self._raw_data,
            )

            # Update inventory for all shows with available ticket count
            available_tickets = event_data.get_available_tickets()
            Logger.info(f"Updating inventory for event {self.slug} with {available_tickets} available tickets")

            if enriched_event.shows:
                for show in enriched_event.shows:
                    original_inventory = show.inventory
                    show.inventory = available_tickets
                    Logger.debug(
                        f"Updated show inventory from {original_inventory} to {available_tickets} for show at {show.time}"
                    )
            else:
                Logger.warn(f"No shows found for event {self.slug}, cannot update inventory")

            Logger.info(f"Successfully enriched event {self.slug} with Showclix ticket data")
            return enriched_event

        except Exception as e:
            Logger.error(f"Error enriching event {self.slug} with Showclix data: {e}")
            return self
