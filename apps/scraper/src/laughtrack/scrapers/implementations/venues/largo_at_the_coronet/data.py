"""Data model for scraped page data from Largo at the Coronet."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.largo_at_the_coronet import LargoAtTheCoronetEvent


@dataclass
class LargoAtTheCoronetPageData:
    """Container for all events extracted from the Largo shows page."""

    event_list: List[LargoAtTheCoronetEvent]

    def has_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
