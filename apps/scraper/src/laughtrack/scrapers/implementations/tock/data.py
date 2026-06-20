"""Data model for Tock scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TockPageData(EventListContainer[JsonLdEvent]):
    """Container for events extracted from Tock rendered Redux state."""

    event_list: List[JsonLdEvent]

