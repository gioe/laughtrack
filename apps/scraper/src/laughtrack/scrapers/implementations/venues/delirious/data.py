"""Page data model for Delirious Comedy Club scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.friendlysky import FriendlySkyEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class DeliriousPageData(EventListContainer[FriendlySkyEvent]):
    """Raw extracted data from the FriendlySky API for Delirious Comedy Club."""

    event_list: List[FriendlySkyEvent]
