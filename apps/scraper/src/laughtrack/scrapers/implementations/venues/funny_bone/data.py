"""Data model for scraped page data from Funny Bone Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.funny_bone import FunnyBoneEvent


@dataclass
class FunnyBonePageData:
    """Container for all events extracted from the Funny Bone shows page."""

    event_list: List[FunnyBoneEvent]

    def has_data(self) -> bool:
        return bool(self.event_list)

    def get_event_count(self) -> int:
        return len(self.event_list)
