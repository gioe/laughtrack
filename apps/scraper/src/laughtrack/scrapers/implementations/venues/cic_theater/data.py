"""Page data for CIC Theater."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.cic_theater import CicTheaterEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class CicTheaterPageData(EventListContainer[CicTheaterEvent]):
    event_list: List[CicTheaterEvent]

