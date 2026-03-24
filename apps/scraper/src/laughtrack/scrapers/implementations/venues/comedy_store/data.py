"""Page data model for The Comedy Store scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_store import ComedyStoreEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComedyStorePageData(EventListContainer[ComedyStoreEvent]):
    """Raw extracted data from a single Comedy Store calendar day page."""

    event_list: List[ComedyStoreEvent]
