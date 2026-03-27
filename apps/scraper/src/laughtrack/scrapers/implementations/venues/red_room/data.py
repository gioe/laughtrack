"""Data model for scraped page data from RED ROOM Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.red_room import RedRoomEvent


@dataclass
class RedRoomPageData:
    """Raw extracted event data from RED ROOM Comedy Club's Wix API."""

    event_list: List[RedRoomEvent]
