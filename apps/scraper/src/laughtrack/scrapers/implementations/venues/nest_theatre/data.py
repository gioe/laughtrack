"""Data model for scraped page data from The Nest Theatre."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.nest_theatre import NestTheatreEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class NestTheatrePageData(EventListContainer[NestTheatreEvent]):
    """Container for NestTheatreEvent objects extracted from the VBO grid."""

    event_list: List[NestTheatreEvent]
