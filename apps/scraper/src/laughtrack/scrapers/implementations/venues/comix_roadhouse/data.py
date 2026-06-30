"""Page data for Comix Roadhouse."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comix_roadhouse import ComixRoadhouseEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComixRoadhousePageData(EventListContainer[ComixRoadhouseEvent]):
    """Raw extracted Comix Roadhouse events."""

    event_list: List[ComixRoadhouseEvent]
