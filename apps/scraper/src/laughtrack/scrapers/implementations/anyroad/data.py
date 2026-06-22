"""Data model for AnyRoad scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class AnyRoadPageData(EventListContainer[JsonLdEvent]):
    """Container for events extracted from the AnyRoad plugin experiences API."""

    event_list: List[JsonLdEvent]
