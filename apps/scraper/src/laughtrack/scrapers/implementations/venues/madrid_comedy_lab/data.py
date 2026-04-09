"""Data model for scraped page data from Madrid Comedy Lab."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.madrid_comedy_lab import MadridComedyLabEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class MadridComedyLabPageData(EventListContainer[MadridComedyLabEvent]):
    """Container for MadridComedyLabEvent objects extracted from the Fienta API."""

    event_list: List[MadridComedyLabEvent]
