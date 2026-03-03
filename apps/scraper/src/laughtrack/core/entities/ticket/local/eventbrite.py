from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class EventbriteTicket:
    """
    Data model representing ticket information from EventBrite offers.

    Contains EventBrite-specific ticket data that can be converted to a standard
    Ticket object when needed.
    """

    # Core ticket information
    price: str  # Price from offer.price (can be string like "25.00" or "0")
    price_currency: str  # Currency code (e.g. "USD")
    url: str  # Purchase URL
    name: str  # Ticket type/name
    availability: str  # Availability status from EventBrite

    # Additional EventBrite-specific fields
    valid_from: Optional[str] = None  # Valid from date if available

    # Raw offer data for debugging
    _raw_offer: Optional[Dict[str, Any]] = None
