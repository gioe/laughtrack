"""Data model for TicketLeap scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TicketleapPageData(EventListContainer[JsonLdEvent]):
    """Container for JSON-LD events extracted from TicketLeap event detail pages."""

    event_list: List[JsonLdEvent]
