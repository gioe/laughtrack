"""
Page data model for SeatEngine API results.

This minimal container implements the EventListContainer protocol.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.foundation.models.types import JSONDict
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SeatEnginePageData(EventListContainer[JSONDict]):
    event_list: List[JSONDict]

    def is_transformable(self) -> bool:
        return bool(self.event_list)
