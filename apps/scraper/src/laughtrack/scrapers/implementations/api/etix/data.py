"""Data model for scraped page data from an Etix venue."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class EtixPageData(EventListContainer[EtixEvent]):
    """Raw extracted event data from an Etix venue page."""

    event_list: List[EtixEvent]
