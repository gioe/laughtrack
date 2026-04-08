"""Data model for scraped page data from The Moon (Tallahassee)."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.the_moon import TheMoonEvent


@dataclass
class TheMoonPageData:
    """Raw extracted event data from The Moon listing page."""

    event_list: List[TheMoonEvent]
