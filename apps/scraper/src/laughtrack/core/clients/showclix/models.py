"""
Data models for Showclix API responses.

This module contains dataclasses that represent the structure of responses
from the Showclix seated events API endpoint.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Union


@dataclass
class ShowclixVenue:
    """Venue information from Showclix API."""

    venue_id: str
    venue_name: str
    address: str
    city: str
    state: str
    zip: str
    seating_chart: Optional[str] = None


@dataclass
class ShowclixPriceLevel:
    """Price level information for an event."""

    level_id: str
    level: str
    inventory: int
    price: str
    active: int
    online_service_fee: float


@dataclass
class ShowclixEventSection:
    """Event section information."""

    arbitrary_id: str
    event_id: str
    section_id: str
    price: str
    description: str
    rank: str
    general_admission: str


@dataclass
class ShowclixSection:
    """Venue section information."""

    section_id: str
    venue_id: str
    section: str
    rank: str


@dataclass
class ShowclixEventData:
    """
    Complete event data response from Showclix seated events API.

    This dataclass represents the JSON response from:
    https://www.showclix.com/api/events/seated/{event_id}
    """

    event_id: str
    event: str
    venue: ShowclixVenue
    purchase_limit: str
    decimals: int
    getDefaultName: bool
    all_levels: Dict[str, ShowclixPriceLevel]
    seatedPriceLevelFees: Dict[str, float]
    allowOrphanSeats: bool
    orphanSeatMessage: str
    seatedLevels: List[str]
    event_sections: Dict[str, ShowclixEventSection]
    sections: Dict[str, ShowclixSection]
    remaining_by_level: Dict[str, int]
    held_by_level: Dict[str, int]
    total_by_level: Dict[str, int]
    section_price_levels: List[Dict]  # Structure varies, keeping as generic dict list
    products: List[Dict]  # Structure varies, keeping as generic dict list
    product_map: List[Dict]  # Structure varies, keeping as generic dict list
    disclose_fee: bool
    fee_verbiage: str
    forceConsecutiveSeats: bool
    forceConsecutiveSeatsMessage: str

    @classmethod
    def from_dict(cls, data: Dict) -> "ShowclixEventData":
        """
        Create a ShowclixEventData instance from a dictionary response.

        Args:
            data: Raw JSON response from Showclix API

        Returns:
            ShowclixEventData instance
        """
        # Parse venue data
        venue_data = data["venue"]
        venue = ShowclixVenue(
            venue_id=venue_data["venue_id"],
            venue_name=venue_data["venue_name"],
            address=venue_data["address"],
            city=venue_data["city"],
            state=venue_data["state"],
            zip=venue_data["zip"],
            seating_chart=venue_data.get("seating_chart"),
        )

        # Parse all_levels data
        all_levels = {}
        for level_id, level_data in data["all_levels"].items():
            all_levels[level_id] = ShowclixPriceLevel(
                level_id=level_data["level_id"],
                level=level_data["level"],
                inventory=level_data["inventory"],
                price=level_data["price"],
                active=level_data["active"],
                online_service_fee=level_data["online_service_fee"],
            )

        # Parse event_sections data
        event_sections = {}
        for section_id, section_data in data["event_sections"].items():
            event_sections[section_id] = ShowclixEventSection(
                arbitrary_id=section_data["arbitrary_id"],
                event_id=section_data["event_id"],
                section_id=section_data["section_id"],
                price=section_data["price"],
                description=section_data["description"],
                rank=section_data["rank"],
                general_admission=section_data["general_admission"],
            )

        # Parse sections data
        sections = {}
        for section_id, section_data in data["sections"].items():
            sections[section_id] = ShowclixSection(
                section_id=section_data["section_id"],
                venue_id=section_data["venue_id"],
                section=section_data["section"],
                rank=section_data["rank"],
            )

        return cls(
            event_id=data["event_id"],
            event=data["event"],
            venue=venue,
            purchase_limit=data["purchase_limit"],
            decimals=data["decimals"],
            getDefaultName=data["getDefaultName"],
            all_levels=all_levels,
            seatedPriceLevelFees=data["seatedPriceLevelFees"],
            allowOrphanSeats=data["allowOrphanSeats"],
            orphanSeatMessage=data["orphanSeatMessage"],
            seatedLevels=data["seatedLevels"],
            event_sections=event_sections,
            sections=sections,
            remaining_by_level=data["remaining_by_level"],
            held_by_level=data["held_by_level"],
            total_by_level=data["total_by_level"],
            section_price_levels=data["section_price_levels"],
            products=data["products"],
            product_map=data["product_map"],
            disclose_fee=data["disclose_fee"],
            fee_verbiage=data["fee_verbiage"],
            forceConsecutiveSeats=data["forceConsecutiveSeats"],
            forceConsecutiveSeatsMessage=data["forceConsecutiveSeatsMessage"],
        )

    def get_primary_price(self) -> Optional[str]:
        """
        Get the primary ticket price for this event.

        Returns:
            The price as a string, or None if no levels available
        """
        if not self.all_levels:
            return None

        # Get the first price level (usually the main admission)
        first_level = next(iter(self.all_levels.values()))
        return first_level.price

    def get_primary_price_with_fees(self) -> Optional[float]:
        """
        Get the primary ticket price including service fees.

        Returns:
            Total price as float, or None if no levels available
        """
        primary_price = self.get_primary_price()
        if not primary_price:
            return None

        base_price = float(primary_price)
        service_fee = self.seatedPriceLevelFees.get(primary_price, 0.0)

        return base_price + service_fee

    def get_available_tickets(self) -> int:
        """
        Get the total number of available tickets across all levels.

        Returns:
            Total available tickets
        """
        return sum(self.remaining_by_level.values())

    def is_sold_out(self) -> bool:
        """
        Check if the event is sold out.

        Returns:
            True if no tickets are available
        """
        return self.get_available_tickets() == 0

    def get_venue_full_address(self) -> str:
        """
        Get the complete venue address as a formatted string.

        Returns:
            Full address string
        """
        return f"{self.venue.address}, {self.venue.city}, {self.venue.state} {self.venue.zip}"
