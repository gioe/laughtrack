"""Data container for TicketWeb scraper page data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ticketweb import TicketWebEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TicketWebPageData(EventListContainer[TicketWebEvent]):
    """Container for events extracted from a TicketWeb-powered detail page."""

    event_list: List[TicketWebEvent]
