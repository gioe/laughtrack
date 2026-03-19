"""Data model for scraped page data from Uptown Theater."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class UptownTheaterPageData(EventListContainer[JsonLdEvent]):
    """Raw extracted data from Uptown Theater event pages."""

    event_list: List[JsonLdEvent]
