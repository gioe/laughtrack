"""Data model for scraped page data from HAHA Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class HaHaComedyClubPageData(EventListContainer[TixrEvent]):
    """
    Data model representing raw extracted data from HAHA Comedy Club calendar pages.

    Contains TixrEvent objects fetched via the Tixr API from short-form
    tixr.com/e/{id} ticket links found on the HAHA calendar.
    """

    event_list: List[TixrEvent]

    def has_event_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
