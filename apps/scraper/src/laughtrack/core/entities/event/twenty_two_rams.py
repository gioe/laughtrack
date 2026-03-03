"""
Data model for a single event from 22Rams ticketing system.

This model represents JSON-LD structured data extracted from 22Rams ticketing pages.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from laughtrack.foundation.models.types import JSONDict


@dataclass
class TwentyTwoRamsEvent:
    """
    Data model representing a single event from 22Rams ticketing pages.

    This corresponds to JSON-LD structured data found on 22Rams event pages,
    following schema.org Event specifications.
    """

    # Core event information
    name: str
    start_date: Optional[str] = None  # ISO format datetime string
    end_date: Optional[str] = None  # ISO format datetime string
    description: Optional[str] = None
    url: Optional[str] = None
    image: Optional[str] = None

    # Location information
    location: Optional[Dict[str, Any]] = None

    # Event status and attendance mode
    event_status: Optional[str] = None
    event_attendance_mode: Optional[str] = None

    # Ticketing information
    offers: Optional[List[Dict[str, Any]]] = None

    # Organizer information
    organizer: Optional[Dict[str, Any]] = None

    # Raw JSON-LD data for debugging/future use
    raw_data: Optional[JSONDict] = None

    # Source URL for tracking
    source_url: Optional[str] = None

    def __post_init__(self):
        """Initialize offers as empty list if None."""
        if self.offers is None:
            self.offers = []

    @classmethod
    def from_json_ld(cls, json_ld_data: JSONDict, source_url: str) -> "TwentyTwoRamsEvent":
        """
        Create a TwentyTwoRamsEvent from JSON-LD structured data.

        Args:
            json_ld_data: JSON-LD event data from the 22Rams page
            source_url: URL where the data was extracted from

        Returns:
            TwentyTwoRamsEvent instance
        """
        offers = json_ld_data.get("offers", [])
        if isinstance(offers, dict):
            offers = [offers]

        return cls(
            name=json_ld_data.get("name", "Unknown Show"),
            start_date=json_ld_data.get("startDate"),
            end_date=json_ld_data.get("endDate"),
            description=json_ld_data.get("description"),
            url=json_ld_data.get("url"),
            image=json_ld_data.get("image"),
            location=json_ld_data.get("location"),
            event_status=json_ld_data.get("eventStatus"),
            event_attendance_mode=json_ld_data.get("eventAttendanceMode"),
            offers=offers,
            organizer=json_ld_data.get("organizer"),
            raw_data=json_ld_data,
            source_url=source_url,
        )

    def get_price_range(self) -> tuple[Optional[float], Optional[float]]:
        """
        Get the minimum and maximum prices from offers.

        Returns:
            Tuple of (min_price, max_price), with None if no valid prices found
        """
        if not self.offers:
            return None, None

        prices = []
        for offer in self.offers:
            try:
                price_str = offer.get("price", "0")
                price = float(price_str)
                if price > 0:
                    prices.append(price)
            except (ValueError, TypeError):
                continue

        if not prices:
            return None, None

        return min(prices), max(prices)

    def is_sold_out(self) -> bool:
        """
        Check if the event is sold out based on offers availability.

        Returns:
            True if all offers are sold out, False otherwise
        """
        if not self.offers:
            return False

        # Check if all offers are not "InStock"
        for offer in self.offers:
            availability = offer.get("availability", "")
            if "InStock" in availability:
                return False

        return True

    def get_venue_name(self) -> Optional[str]:
        """
        Extract venue name from location data.

        Returns:
            Venue name if available, None otherwise
        """
        if not self.location:
            return None

        return self.location.get("name")
