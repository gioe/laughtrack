"""Data model for scraped page data from Laugh Factory Covina."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class LaughFactoryCovinaPageData(EventListContainer[TixrEvent]):
    """
    Data model representing raw extracted data from Laugh Factory Covina pages.

    Contains TixrEvent objects fetched via the Tixr API, following the
    standard PageData / EventListContainer pattern.
    """

    event_list: List[TixrEvent]
    tixr_urls: List[str]  # Source URLs for reference/debugging

    def has_event_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
