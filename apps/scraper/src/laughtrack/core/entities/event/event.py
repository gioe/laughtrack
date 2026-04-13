from __future__ import annotations
"""Data models for scraping and processing event data."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class PostalAddress:
    street_address: str
    address_locality: str
    postal_code: str
    address_region: str
    address_country: str


@dataclass
class Place:
    name: str
    address: PostalAddress


@dataclass
class Offer:
    url: str
    price_currency: str
    price: str
    availability: str
    valid_from: Optional[datetime] = None
    name: Optional[str] = None


@dataclass
class Organization:
    name: str
    url: str


@dataclass
class Person:
    name: str


@dataclass
class JsonLdEvent(ShowConvertible):
    """Base class for all event types."""

    name: str
    start_date: datetime
    location: Place
    offers: List[Offer]
    url: str
    description: str
    performers: Optional[List[Person]] = None
    event_status: Optional[str] = None
    event_attendance_mode: Optional[str] = None
    image: Optional[str] = None
    organizer: Optional[Organization] = None
    event_type: str = "Event"
    same_as: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[object]:
        """Factory method to create a Show from an Event and Club.

        Args:
            event: The Event instance to convert
            club: The Club instance for the show
            enhanced: Whether to use enhanced processing for tickets and tags
            source_url: Optional source URL for enhanced URL processing

        Returns:
            Show: A new Show instance created from the event
        """
        # Import only when needed to avoid circular imports
        from laughtrack.core.entities.comedian.model import Comedian
        from laughtrack.core.entities.ticket.model import Ticket
        from laughtrack.core.entities.show.model import Show

        # Convert performers to Comedians
        lineup = [Comedian(name=performer.name) for performer in self.performers] if self.performers else []

        # Convert offers to Tickets with optional enhancement
        if enhanced:
            from laughtrack.utilities.domain.show.enhancement import ShowEnhancement

            tickets = ShowEnhancement.enhance_tickets_from_event(self)
            supplied_tags = ShowEnhancement.extract_advanced_tags_from_event(self)
        else:
            # Basic conversion for backward compatibility
            tickets = [Ticket.from_offer(offer) for offer in self.offers] if self.offers else []
            supplied_tags = []

        # Prefer sameAs for show_page_url when it points to the club's own site,
        # keeping self.url (often a third-party ticket link) for ticket purchase
        show_page_url = self.same_as if self.same_as else self.url

        # Create the basic show instance
        show = Show(
            name=self.name,
            club_id=club.id,
            date=self.start_date,
            show_page_url=show_page_url,
            lineup=lineup,
            tickets=tickets,
            description=self.description,
            room=None,  # Default room handling
            supplied_tags=supplied_tags,
        )

        # Apply enhanced processing if enabled
        if enhanced:
            from laughtrack.utilities.domain.show.enhancement import ShowEnhancement
            # Validate and fix any data issues
            show, warnings = ShowEnhancement.validate_and_fix_show_data(show)

            # Log any warnings from validation
            for warning in warnings:
                Logger.warning(f"Show data fix applied: {warning}")

        return show

    @classmethod
    def from_json_ld(cls, data: dict) -> "JsonLdEvent":
        """Create an Event instance from JSON-LD data."""
        # For now, create using the base parser; specialized subtypes can override
        return cls._create_from_json_ld(data)

    @classmethod
    def _create_from_json_ld(cls, data: dict) -> "JsonLdEvent":
        """Internal method to create an Event instance from JSON-LD data."""
        try:
            # Validate required fields
            url, name, start_date_str = cls._validate_required_fields(data)

            # Parse complex fields
            location = cls._parse_location(data)
            offers = cls._parse_offers(data)
            organizer = cls._parse_organizer(data)
            performers = cls._parse_performers(data)

            # Parse sameAs — may be a string or list of strings; take the first
            same_as_raw = data.get("sameAs")
            if isinstance(same_as_raw, list):
                same_as = same_as_raw[0] if same_as_raw else None
            elif isinstance(same_as_raw, str):
                same_as = same_as_raw
            else:
                same_as = None

            return cls(
                name=name,
                start_date=parse_event_date(start_date_str),
                location=location,
                event_status=data.get("eventStatus"),
                event_attendance_mode=data.get("eventAttendanceMode"),
                offers=offers,
                url=url,
                image=data.get("image"),
                description=data.get("description", ""),
                organizer=organizer,
                performers=performers,
                event_type=data.get("@type", "Event"),
                same_as=same_as,
            )
        except KeyError as e:
            raise KeyError(f"Missing required field in JSON-LD data: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid or missing required field in JSON-LD data: {e}")

    @classmethod
    def _validate_required_fields(cls, data: dict) -> tuple[str, str, str]:
        """Validate and extract required fields from JSON-LD data."""
        url = data.get("url")
        name = data.get("name")
        start_date_str = data.get("startDate")

        # Fallback: some JSON-LD puts the URL only under offers
        if not url:
            offers_data = data.get("offers")
            if isinstance(offers_data, dict):
                url = offers_data.get("url")
            elif isinstance(offers_data, list):
                for offer in offers_data:
                    if isinstance(offer, dict) and offer.get("url"):
                        url = offer["url"]
                        break
        if not url:
            raise ValueError("Event missing required 'url' field (and no 'offers.url' fallback)")
        if not name:
            raise ValueError("Event missing required 'name' field")
        if not start_date_str:
            raise ValueError("Event missing required 'startDate' field")

        return url, name, start_date_str

    @classmethod
    def _parse_location(cls, data: dict) -> Place:
        """Parse location data from JSON-LD."""
        location_obj = data.get("location", {}) or {}
        address_data = location_obj.get("address", {})

        if isinstance(address_data, dict):
            address = PostalAddress(
                street_address=address_data.get("streetAddress", ""),
                address_locality=address_data.get("addressLocality", ""),
                address_region=address_data.get("addressRegion", ""),
                postal_code=address_data.get("postalCode", ""),
                address_country=address_data.get("addressCountry", ""),
            )
        elif isinstance(address_data, str):
            address = PostalAddress(
                street_address=address_data,
                address_locality="",
                address_region="",
                postal_code="",
                address_country="",
            )
        else:
            address = PostalAddress(
                street_address="",
                address_locality="",
                address_region="",
                postal_code="",
                address_country="",
            )

        # Prefer the location name if provided; fall back to top-level name
        place_name = location_obj.get("name") or data.get("name", "")
        return Place(name=place_name, address=address)

    @classmethod
    def _parse_offers(cls, data: dict) -> List[Offer]:
        """Parse offers data from JSON-LD."""
        offers: List[Offer] = []
        offers_data = data.get("offers")

        if not offers_data:
            return offers

        # Normalize to list
        if isinstance(offers_data, list):
            offers_list = offers_data
        elif isinstance(offers_data, dict):
            offers_list = [offers_data]
        else:
            offers_list = []

        for offer in offers_list:
            valid_from = None
            if "validFrom" in offer:
                try:
                    valid_from = parse_event_date(offer["validFrom"])
                except Exception:
                    valid_from = None

            offers.append(
                Offer(
                    url=offer.get("url", ""),
                    price_currency=offer.get("priceCurrency", ""),
                    price=offer.get("price", ""),
                    availability=offer.get("availability", ""),
                    valid_from=valid_from,
                    name=offer.get("name"),
                )
            )

        return offers

    @classmethod
    def _parse_organizer(cls, data: dict) -> Optional[Organization]:
        """Parse organizer data from JSON-LD."""
        organizer_data = data.get("organizer")
        if organizer_data:
            return Organization(name=organizer_data.get("name", ""), url=organizer_data.get("url", ""))
        return None

    @classmethod
    def _parse_performers(cls, data: dict) -> List[Person]:
        """Parse performers data from JSON-LD."""
        performers: List[Person] = []
        performers_data = data.get("performer")

        if not performers_data:
            return performers

        # Normalize to list
        if isinstance(performers_data, list):
            performers_list = performers_data
        elif isinstance(performers_data, dict):
            performers_list = [performers_data]
        else:
            performers_list = []

        for p in performers_list:
            if isinstance(p, dict) and "name" in p:
                performers.append(Person(name=p["name"]))

        return performers


@dataclass
class ComedyEvent(JsonLdEvent):
    """Specialized class for comedy events."""

    event_type: str = "ComedyEvent"

    @classmethod
    def from_json_ld(cls, data: dict) -> "ComedyEvent":
        """Create a ComedyEvent instance from JSON-LD data."""
        if data.get("@type") != "ComedyEvent":
            raise ValueError("JSON-LD data is not a ComedyEvent")

        # Use the base class's _create_from_json_ld method
        event = cls._create_from_json_ld(data)
        return cls(**event.__dict__)


def parse_event_date(date_str):
    # Try ISO format first
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        pass
    # Try common alternative formats
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            pass
    raise ValueError(f"Unrecognized date format: {date_str}")
