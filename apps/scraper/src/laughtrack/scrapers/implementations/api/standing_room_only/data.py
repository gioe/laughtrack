"""Page data container for the Standing Room Only platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.standing_room_only import StandingRoomOnlyEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class StandingRoomOnlyPageData(EventListContainer[StandingRoomOnlyEvent]):
    """Raw extracted show data from the Standing Room Only ReadLiveEvents feed."""

    event_list: List[StandingRoomOnlyEvent]
