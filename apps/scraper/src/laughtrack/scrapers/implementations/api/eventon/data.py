"""Data model for EventON scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.eventon import EventONEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class EventONPageData(EventListContainer[EventONEvent]):
    """Container for future events extracted from an EventON calendar."""

    event_list: List[EventONEvent]
