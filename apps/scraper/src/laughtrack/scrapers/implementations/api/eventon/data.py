"""Data model for EventON scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.eventon import EventONEvent


@dataclass
class EventONPageData:
    """Container for future events extracted from an EventON calendar."""

    event_list: List[EventONEvent]
