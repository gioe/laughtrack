"""Data model for scraped page data from a JetBook venue iframe."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.jetbook import JetBookEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class JetBookPageData(EventListContainer[JetBookEvent]):
    """Raw extracted event data from a JetBook (Bubble.io) iframe."""

    event_list: List[JetBookEvent]
