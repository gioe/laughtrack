"""Page data container for the WellAttended platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.wellattended import WellAttendedEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class WellAttendedPageData(EventListContainer[WellAttendedEvent]):
    """Raw extracted show data from WellAttended /events/<slug> RSC pages."""

    event_list: List[WellAttendedEvent]
