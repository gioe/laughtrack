"""Page data for Soboba Casino Resort calendar pages."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.soboba_casino_resort import SobobaCasinoResortEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SobobaCasinoResortPageData(EventListContainer[SobobaCasinoResortEvent]):
    """Raw extracted events from one Soboba calendar page."""

    event_list: List[SobobaCasinoResortEvent]
