"""
Ticket and sales-related Eventbrite API models.

This module contains dataclass definitions for ticket pricing,
sales status, and payment information in Eventbrite API responses.
"""

from dataclasses import dataclass
from typing import List, Optional

from laughtrack.foundation.models.api.eventbrite.base_models import EventbriteDateTime, EventbritePrice


@dataclass
class EventbriteTicketAvailability:
    """Ticket availability and pricing information."""

    has_available_tickets: bool
    is_sold_out: bool
    waitlist_available: bool = False
    minimum_ticket_price: Optional[EventbritePrice] = None
    maximum_ticket_price: Optional[EventbritePrice] = None
    start_sales_date: Optional[EventbriteDateTime] = None

    @classmethod
    def from_json_dict(cls, data: dict) -> "EventbriteTicketAvailability":
        """Create EventbriteTicketAvailability from JSON dict."""
        minimum_price = None
        if data.get("minimum_ticket_price"):
            minimum_price = EventbritePrice.from_json_dict(data["minimum_ticket_price"])

        maximum_price = None
        if data.get("maximum_ticket_price"):
            maximum_price = EventbritePrice.from_json_dict(data["maximum_ticket_price"])

        start_sales_date = None
        if data.get("start_sales_date"):
            start_sales_date = EventbriteDateTime.from_json_dict(data["start_sales_date"])

        return cls(
            has_available_tickets=data.get("has_available_tickets", False),
            is_sold_out=data.get("is_sold_out", False),
            waitlist_available=data.get("waitlist_available", False),
            minimum_ticket_price=minimum_price,
            maximum_ticket_price=maximum_price,
            start_sales_date=start_sales_date,
        )


@dataclass
class EventbriteExternalTicketing:
    """External ticketing provider information."""

    external_url: str = ""
    ticketing_provider_name: str = ""
    is_free: bool = False
    minimum_ticket_price: Optional[EventbritePrice] = None
    maximum_ticket_price: Optional[EventbritePrice] = None
    sales_start: str = ""
    sales_end: str = ""


@dataclass
class EventbriteSalesStatus:
    """Event sales status information."""

    sales_status: str
    start_sales_date: Optional[EventbriteDateTime] = None


@dataclass
class EventbriteOfflineSettings:
    """Offline payment settings."""

    payment_method: str
    instructions: str = ""


@dataclass
class EventbriteCheckoutSettings:
    """Checkout and payment settings."""

    created: str
    changed: str
    country_code: str = ""
    currency_code: str = ""
    checkout_method: str = ""
    user_instrument_vault_id: str = ""
    offline_settings: Optional[List[EventbriteOfflineSettings]] = None
