"""
Data model for scraped page data from JSON-LD extraction.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class JsonLdPageData(EventListContainer[JsonLdEvent]):
    """
    Data model representing raw extracted data from a scraped webpage.

    This contains the structured JSON-LD Event objects along with the source URL.
    """

    event_list: List[JsonLdEvent]
