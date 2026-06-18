"""Page data model for classic SeatEngine HTML results."""

from dataclasses import dataclass, field
from typing import List

from laughtrack.foundation.models.types import JSONDict
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SeatEngineClassicPageData(EventListContainer[JSONDict]):
    event_list: List[JSONDict] = field(default_factory=list)

    def is_transformable(self) -> bool:
        return bool(self.event_list)
