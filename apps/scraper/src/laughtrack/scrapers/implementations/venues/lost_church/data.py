"""Data model for scraped page data from The Lost Church."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.lost_church import LostChurchEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class LostChurchPageData(EventListContainer[LostChurchEvent]):
    """Container for LostChurchEvent objects extracted from the PatronTicket API."""

    event_list: List[LostChurchEvent]
