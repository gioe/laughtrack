"""
Data model for scraped page data from Comic Strip Live (EventBrite integration).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
if TYPE_CHECKING:  # Avoid circular import at runtime
    from laughtrack.core.entities.event.rodneys import RodneyEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.models.api.eventbrite import EventbriteTicket
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.utilities.domain.show.factory import is_dj_set_show


@dataclass
class EventbriteEvent(ShowConvertible):
    """
    Data model representing a single EventBrite event extracted from Comic Strip Live.

    This model handles data from EventBrite event pages, including both JSON-LD
    structured data and fallback HTML extraction.
    """

    # Core event information
    name: str
    event_url: str
    start_date: str  # ISO format datetime string

    # Optional event details
    description: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None

    # Performer information
    performers: Optional[List[str]] = None

    # Ticket information - now using EventbriteTicket objects
    ticket_offers: Optional[List[EventbriteTicket]] = None

    # Data source indicators
    data_source_type: str = "json_ld"  # "json_ld" or "html_extraction"

    # Raw data preservation for debugging
    _raw_json_ld: Optional[Dict[str, Any]] = None
    _raw_html_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_api_model(cls, api_event) -> "EventbriteEvent":
        """
        Convert from Eventbrite API model to domain EventbriteEvent.

        Args:
            api_event: EventbriteEvent from service_clients.api.eventbrite.models

        Returns:
            Domain EventbriteEvent instance
        """
        # Extract event name from API model's name field (EventbriteTextHtml)
        event_name = ""
        if hasattr(api_event.name, "text"):
            event_name = api_event.name.text
        elif hasattr(api_event.name, "html"):
            # Strip HTML if needed
            import re

            event_name = re.sub(r"<[^>]+>", "", api_event.name.html)
        else:
            event_name = str(api_event.name) if api_event.name else ""

        # Extract start date from API model
        start_date = ""
        if api_event.start and hasattr(api_event.start, "utc"):
            start_date = api_event.start.utc

        # Extract description from API model
        description = None
        if api_event.description:
            if hasattr(api_event.description, "text"):
                description = api_event.description.text
            elif hasattr(api_event.description, "html"):
                # Strip HTML if needed
                import re

                description = re.sub(r"<[^>]+>", "", api_event.description.html)

        # Extract location information from venue
        location_name = None
        location_address = None
        if api_event.venue:
            if hasattr(api_event.venue, "name"):
                location_name = api_event.venue.name
            if hasattr(api_event.venue, "address") and api_event.venue.address:
                # Build address string from address components
                address_parts = []
                if hasattr(api_event.venue.address, "address_1") and api_event.venue.address.address_1:
                    address_parts.append(api_event.venue.address.address_1)
                if hasattr(api_event.venue.address, "city") and api_event.venue.address.city:
                    address_parts.append(api_event.venue.address.city)
                if hasattr(api_event.venue.address, "region") and api_event.venue.address.region:
                    address_parts.append(api_event.venue.address.region)
                location_address = ", ".join(address_parts) if address_parts else None

        return cls(
            name=event_name,
            event_url=api_event.url,
            start_date=start_date,
            description=description,
            location_name=location_name,
            location_address=location_address,
            performers=None,  # Will need to be extracted separately if available
            ticket_offers=None,  # Will need to be converted from ticket_availability if available
            data_source_type="api",
            _raw_json_ld=None,
            _raw_html_data={"api_event": api_event.__dict__},
        )

    def to_show(self, club: Club, enhanced: bool = True, url: str | None = None):
        """Transform EventbriteEvent object to Show objects with EventBrite-specific processing."""
        try:
            if is_dj_set_show(self.name):
                Logger.info(f"Skipping DJ set show: {self.name!r}")
                return None

            # Parse the date
            if self.start_date:
                try:
                    show_date = DateTimeUtils.parse_datetime_with_timezone(
                        self.start_date, club.timezone or "America/New_York"
                    )
                except Exception as e:
                    Logger.warn(f"Error parsing date '{self.start_date}': {e}")
                    return None
            else:
                Logger.warn("No date found in EventBrite event data")
                return None

            # Extract lineup from performers
            lineup = []
            if self.performers:
                for performer_name in self.performers:
                    if performer_name and performer_name.strip():
                        comedian = Comedian(name=performer_name.strip())
                        lineup.append(comedian)

            # If no structured performers, try to extract from event name
            if not lineup:
                lineup = self._extract_lineup_from_title(self.name)

            # Extract tickets from ticket offers
            tickets = []
            if self.ticket_offers:
                for eventbrite_ticket in self.ticket_offers:
                    try:
                        price = float(str(eventbrite_ticket.price).replace("$", "").replace(",", ""))
                    except (ValueError, TypeError):
                        price = 0.0

                    ticket_url = eventbrite_ticket.url or self.event_url
                    ticket_type = eventbrite_ticket.name or "General Admission"

                    # Check availability for sold out status
                    sold_out = "OutOfStock" in (eventbrite_ticket.availability or "")

                    ticket = Ticket(price=price, purchase_url=ticket_url, type=ticket_type, sold_out=sold_out)
                    tickets.append(ticket)

            # If no ticket offers, create a basic ticket
            if not tickets:
                # No per-ticket availability data when ticket_offers is absent; default to not sold out
                tickets.append(Ticket(price=0.0, purchase_url=self.event_url, type="General Admission", sold_out=False))

            # Create show object
            show = Show(
                name=self.name,
                club_id=club.id,
                date=show_date,
                show_page_url=self.event_url,
                lineup=lineup,
                tickets=tickets,
                supplied_tags=["eventbrite", "comedy"],
                description=self.description or "",
                timezone=club.timezone,
                room="",
                popularity=0.0,
            )

            return show

        except Exception as e:
            Logger.error(f"Failed to transform EventBrite Event data: {e}")
            return None

    def _extract_lineup_from_title(self, event_name: str) -> List[Comedian]:
        """
        Extract performer names from event title as fallback.

        Args:
            event_name: The name/title of the event

        Returns:
            List of Comedian objects extracted from the title
        """
        lineup = []

        try:
            # Simple extraction: look for names in the title
            # This is basic and could be improved with better parsing
            if " & " in event_name or " and " in event_name:
                # Split on common separators
                parts = event_name.replace(" & ", ",").replace(" and ", ",").split(",")
                for part in parts:
                    name = part.strip()
                    if name and len(name) > 2:  # Basic filter
                        # Remove common event words
                        cleaned_name = self._clean_performer_name(name)
                        if cleaned_name:
                            comedian = Comedian(name=cleaned_name)
                            lineup.append(comedian)

        except Exception as e:
            Logger.warn(f"Error extracting lineup from title: {e}")

        return lineup

    def _clean_performer_name(self, name: str) -> str:
        """
        Clean performer name by removing common event-related words.

        Args:
            name: Raw performer name from title

        Returns:
            Cleaned performer name or empty string if not valid
        """
        # Common words to remove/filter
        skip_words = {
            "show",
            "comedy",
            "live",
            "standup",
            "stand-up",
            "event",
            "presents",
            "featuring",
            "with",
            "special",
            "guest",
            "performance",
            "night",
            "evening",
        }

        # Remove common punctuation and extra whitespace
        cleaned = name.strip().replace("(", "").replace(")", "").replace(":", "").strip()

        # Skip if it's mostly non-alphabetic or contains skip words
        if not cleaned or len(cleaned) < 3:
            return ""

        words = cleaned.lower().split()
        if any(word in skip_words for word in words):
            return ""

        return cleaned

    def to_rodney_event(self) -> "RodneyEvent":
        """Convert this EventbriteEvent to a RodneyEvent."""
        # Local import to avoid circular import at module load time
        from laughtrack.core.entities.event.rodneys import RodneyEvent
        from datetime import datetime

        # Extract date from start_date string
        date_time = None
        if self.start_date:
            try:
                # Handle various datetime formats
                date_str = self.start_date.replace("Z", "+00:00")
                date_time = datetime.fromisoformat(date_str)
            except (ValueError, AttributeError):
                # Fallback to current time if parsing fails
                date_time = datetime.now()
        else:
            date_time = datetime.now()

        # Extract ticket info
        ticket_info = self._extract_ticket_info()

        return RodneyEvent(
            id=self._generate_id_from_url(self.event_url),
            title=self.name or "Unknown Event",
            date_time=date_time,
            # source_url removed
            source_type="eventbrite",
            description=self.description,
            performers=self.performers,
            ticket_info=ticket_info,
            location=self.location_name,
            image_url=None,  # EventbriteEvent doesn't have image_url field
            _raw_data=self.__dict__,
        )

    def _generate_id_from_url(self, url: str) -> str:
        """Generate a unique ID from URL when no ID is available."""
        return url.split("/")[-1] or url.split("/")[-2]

    def _extract_ticket_info(self) -> Optional[Dict[str, Any]]:
        """Extract ticket information from this EventbriteEvent object."""
        if not self.ticket_offers:
            return None

        ticket_info = {}
        min_price = None
        max_price = None

        for ticket_offer in self.ticket_offers:
            # EventbriteTicket objects have a price attribute
            if hasattr(ticket_offer, "price") and ticket_offer.price is not None:
                try:
                    # Convert price to float, handling string formats like "$20.00"
                    price = float(str(ticket_offer.price).replace("$", "").replace(",", ""))
                    if min_price is None or price < min_price:
                        min_price = price
                    if max_price is None or price > max_price:
                        max_price = price
                except (ValueError, TypeError):
                    continue

        if min_price is not None:
            ticket_info["min_price"] = min_price
        if max_price is not None:
            ticket_info["max_price"] = max_price

        ticket_info["currency"] = "USD"  # Default currency
        ticket_info["purchase_url"] = self.event_url

        return ticket_info if ticket_info else None
