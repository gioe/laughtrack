"""Data model for scraped page data from Off Cabot Comedy and Events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.off_cabot import OffCabotEvent


@dataclass
class OffCabotPageData:
    """Container for events extracted from an Off Cabot event detail page."""

    event_list: List[OffCabotEvent]

    def has_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
