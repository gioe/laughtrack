"""Page data model for SeatEngine v3 API results."""

from dataclasses import dataclass
from typing import List

from laughtrack.foundation.models.types import JSONDict
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SeatEngineV3PageData(EventListContainer[JSONDict]):
    """Container for a flat list of (event, show) dicts ready for transformation."""

    event_list: List[JSONDict]

    def is_transformable(self) -> bool:
        return bool(self.event_list)
