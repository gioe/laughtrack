"""Data model for BookTix scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.booktix import BookTixEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class BookTixPageData(EventListContainer[BookTixEvent]):
    """Container for showtime events extracted from a BookTix production page."""

    event_list: List[BookTixEvent]
