"""Data model for scraped page data from a Vivenu seller page."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.vivenu import VivenuEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class VivenuPageData(EventListContainer[VivenuEvent]):
    """Raw extracted event data from a Vivenu seller page."""

    event_list: List[VivenuEvent]
