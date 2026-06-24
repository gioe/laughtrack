"""Page data for Lesher Center."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.lesher_center import LesherCenterEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class LesherCenterPageData(EventListContainer[LesherCenterEvent]):
    """Container for Lesher Center comedy event instances."""

    event_list: List[LesherCenterEvent]
