"""
Data model for scraped page data from Improv venues.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ImprovPageData(EventListContainer[JsonLdEvent]):
    """
    Data model representing raw extracted data from Improv venue pages.

    This contains the JSON-LD event dictionaries extracted from improv.com venues,
    following the standard PageData pattern.
    """

    event_list: List[JsonLdEvent]
