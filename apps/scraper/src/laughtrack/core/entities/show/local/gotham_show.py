"""Gotham Comedy Club show data model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GothamShow:
    """
    Data model representing a single show within a Gotham Comedy Club event.

    This corresponds to individual shows within the 'shows' array in the S3 JSON response.
    Each event can have multiple shows (different times).
    """

    time: str  # e.g., "7:30 pm"
    listing_url: str  # Showclix ticket URL
    date: str  # ISO datetime string for this specific show
    inventory: Optional[int] = None  # Available tickets

    def __post_init__(self):
        """Validate required fields."""
        if not self.time or not self.listing_url or not self.date:
            raise ValueError("GothamShow requires time, listing_url, and date")
