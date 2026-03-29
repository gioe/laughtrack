"""Data model for scraped page data from a Vivenu seller page."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.vivenu import VivenuEvent


@dataclass
class VivenuPageData:
    """Raw extracted event data from a Vivenu seller page."""

    event_list: List[VivenuEvent]
