"""Data model for BookTix scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.booktix import BookTixEvent


@dataclass
class BookTixPageData:
    """Container for showtime events extracted from a BookTix production page."""

    event_list: List[BookTixEvent]
