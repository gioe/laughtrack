"""Data model for scraped page data from Ice House Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ice_house import IceHouseEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class IceHousePageData(EventListContainer[IceHouseEvent]):
    """Raw extracted event data from Ice House Comedy Club's Tockify API."""

    event_list: List[IceHouseEvent]
