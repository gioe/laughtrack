"""Data model for scraped page data from a Multipass venue box-office page."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.multipass import MultipassEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class MultipassPageData(EventListContainer[MultipassEvent]):
    """Raw extracted event data from a Multipass venue listing page."""

    event_list: List[MultipassEvent]
