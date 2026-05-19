"""Page data for accesso ShoWare performance responses."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.showare import ShoWarePerformance
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ShoWarePageData(EventListContainer[ShoWarePerformance]):
    event_list: List[ShoWarePerformance]
