"""Data model for Improv venue events."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class ImprovEvent(ShowConvertible):
    """
    Data model representing a single event from Improv venues.

    This corresponds to the JSON-LD event structure found on improv.com venues,
    processed for easy transformation to Show objects.
    """

    # Core event information
    name: str
    start_date: datetime
    url: str

    # Optional event details
    description: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None

    # Performer information
    performers: Optional[List[str]] = None

    # Ticket/offer information
    offers: Optional[List[Dict[str, Any]]] = None

    # Raw event data for debugging
    _raw_event_data: Optional[Dict[str, Any]] = None

    def has_tickets(self) -> bool:
        """Check if this event has ticket offers."""
        return bool(self.offers and len(self.offers) > 0)

    def get_ticket_urls(self) -> List[str]:
        """Get all ticket purchase URLs for this event."""
        if not self.offers:
            return []
        return [offer.get("url", "") for offer in self.offers if offer.get("url")]

    def matches_event_id(self, event_id: str) -> bool:
        """Check if this event matches the given event ID by checking offer URLs."""
        ticket_urls = self.get_ticket_urls()
        return any(event_id in url for url in ticket_urls)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """
        Convert the ImprovEvent to a Show object.

        Args:
            club: The Club instance for the show
            enhanced: Whether to use enhanced processing (currently not implemented for ImprovEvent)
            url: Optional URL override for the show page

        Returns:
            Show instance or None if conversion fails
        """
        if not self.name or not self.start_date:
            return None

        # Convert performers to Comedians
        lineup = [Comedian(name=performer) for performer in self.performers] if self.performers else []

        # Convert offers to basic Tickets (enhanced processing not yet supported for ImprovEvent)
        tickets = []
        if self.offers:

            for offer in self.offers:
                # Create basic ticket from offer dict
                raw_price = offer.get("price", "")
                price = float(raw_price) if raw_price else None
                availability = offer.get("availability", "")
                is_sold_out = "SoldOut" in availability or "OutOfStock" in availability
                ticket_type = offer.get("name") or "General Admission"
                if "schema.org/" in ticket_type:
                    ticket_type = "General Admission"
                ticket = Ticket(
                    price=price,
                    purchase_url=offer.get("url", ""),
                    type=ticket_type,
                    sold_out=is_sold_out,
                )
                tickets.append(ticket)

        # Create the basic show instance
        show = Show(
            name=self.name,
            club_id=club.id,
            date=self.start_date,
            show_page_url=url or self.url,
            lineup=lineup,
            tickets=tickets,
            description=self.description,
            room=None,  # Default room handling
            supplied_tags=[],  # Basic conversion for now
        )

        return show
