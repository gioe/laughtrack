"""Data model for scraped page data from Laugh Factory Reno."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tixologi import TixologiEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class LaughFactoryRenoPageData(EventListContainer[TixologiEvent]):
    """
    Data model representing raw extracted data from Laugh Factory Reno pages.

    Contains TixologiEvent objects parsed from the Laugh Factory CMS HTML,
    following the standard PageData / EventListContainer pattern.
    """

    event_list: List[TixologiEvent]

    def has_event_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
