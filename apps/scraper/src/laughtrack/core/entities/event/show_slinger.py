"""Data model for a single event from a ShowSlinger widget."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ShowSlingerEvent:
    """A single showtime extracted from a ShowSlinger combo widget.

    Each event card in the widget may list multiple showtimes; the extractor
    expands those into one ShowSlingerEvent per showtime so that each instance
    maps to exactly one Show.
    """

    name: str
    date_time: datetime
    ticket_url: str
    ticket_id: str
    price: Optional[float] = None
    image_url: Optional[str] = None
    sold_out: bool = False
