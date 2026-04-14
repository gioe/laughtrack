"""Data model for scraped page data from an Etix venue."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.etix import EtixEvent


@dataclass
class EtixPageData:
    """Raw extracted event data from an Etix venue page."""

    event_list: List[EtixEvent]
