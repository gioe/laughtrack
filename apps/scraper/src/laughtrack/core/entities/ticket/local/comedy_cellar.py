from dataclasses import dataclass
from typing import Optional


@dataclass
class ComedyCellarTicket:
    """
    Data model representing ticket information from Comedy Cellar API.

    Contains all the raw ticket data from the API response for a specific show,
    which can be converted to a standard Ticket object when needed.
    """

    # Core ticket information
    show_id: int
    cover_charge: float  # Price from "cover" field
    sold_out: bool  # From "soldout" field
    purchase_url: str  # Generated reservation URL

    # Additional API fields that might be useful
    api_timestamp: Optional[int] = None  # From "timestamp" field
    room_id: Optional[int] = None  # From "roomId" field
    show_time: Optional[str] = None  # From "time" field
    description: Optional[str] = None  # From "description" field
    note: Optional[str] = None  # From "note" field

    # Raw API data for debugging/future use
    raw_api_data: Optional[dict] = None
