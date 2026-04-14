"""Data model for scraped page data from Brew HaHa Comedy at River."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent


@dataclass
class BrewHaHaRiverPageData:
    """JSON-LD events filtered to the River venue only."""

    event_list: List[JsonLdEvent]
