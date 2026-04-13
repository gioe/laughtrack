"""Data model for Levity Live scraped page data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class LevityLivePageData(EventListContainer[JsonLdEvent]):
    """Aggregated event data from Levity Live calendar + comic detail pages."""

    event_list: List[JsonLdEvent]
