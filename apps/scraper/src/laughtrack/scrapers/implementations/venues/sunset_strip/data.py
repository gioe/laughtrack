"""Data model for scraped page data from Sunset Strip Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.squadup import SquadUpEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SunsetStripPageData(EventListContainer[SquadUpEvent]):
    """
    Data model representing raw extracted data from the SquadUP API for
    Sunset Strip Comedy Club (Austin, TX).

    Contains SquadUpEvent objects fetched from the SquadUP events API,
    following the standard PageData / EventListContainer pattern.
    """

    event_list: List[SquadUpEvent]

    def has_event_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
