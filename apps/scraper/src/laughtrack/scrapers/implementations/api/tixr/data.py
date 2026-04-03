"""Data model for scraped Tixr page data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TixrPageData(EventListContainer[TixrEvent]):
    """Container for TixrEvent objects resolved from a venue calendar page."""

    event_list: List[TixrEvent]

    def has_event_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
