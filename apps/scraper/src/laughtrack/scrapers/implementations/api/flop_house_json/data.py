"""Data container for Flop House JSON events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.flop_house_json import FlopHouseJsonEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class FlopHouseJsonPageData(EventListContainer[FlopHouseJsonEvent]):
    """Container for events parsed from Flop House JSON feeds."""

    event_list: List[FlopHouseJsonEvent]
