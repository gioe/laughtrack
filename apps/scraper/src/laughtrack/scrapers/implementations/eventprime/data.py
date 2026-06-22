"""Data model for EventPrime scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class EventPrimePageData(EventListContainer[JsonLdEvent]):
    """Container for events extracted from the EventPrime get_events API."""

    event_list: List[JsonLdEvent]
