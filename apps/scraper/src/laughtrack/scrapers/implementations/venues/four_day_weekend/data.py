"""Data model for scraped page data from Four Day Weekend Comedy."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.four_day_weekend import FourDayWeekendEvent


@dataclass
class FourDayWeekendPageData:
    """Container for all performances extracted from the OvationTix API."""

    event_list: List[FourDayWeekendEvent]

    def has_json_ld_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
