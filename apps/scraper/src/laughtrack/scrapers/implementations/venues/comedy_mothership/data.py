"""Data model for scraped page data from Comedy Mothership."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_mothership import ComedyMothershipEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComedyMothershipPageData(EventListContainer[ComedyMothershipEvent]):
    """
    Data model representing raw extracted data from Comedy Mothership pages.

    Contains ComedyMothershipEvent objects parsed from the server-rendered
    show listing HTML, following the standard PageData / EventListContainer pattern.
    """

    event_list: List[ComedyMothershipEvent]

    def has_event_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
