"""
Data model for scraped page data from Improv venues.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.improv import ImprovEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ImprovPageData(EventListContainer[ImprovEvent]):
    """
    Data model representing raw extracted data from Improv venue pages.

    This contains ImprovEvent objects extracted from improv.com venues,
    following the standard PageData pattern.
    """

    event_list: List[ImprovEvent]
