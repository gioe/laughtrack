"""Data model for scraped page data from Comedy @ The Carlson."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_at_the_carlson import ComedyAtTheCarlsonEvent


@dataclass
class ComedyAtTheCarlsonPageData:
    """Container for all performances extracted from the OvationTix API."""

    event_list: List[ComedyAtTheCarlsonEvent]

    def has_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
