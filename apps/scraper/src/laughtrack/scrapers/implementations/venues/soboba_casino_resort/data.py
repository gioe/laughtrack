"""Page data for Soboba Casino Resort calendar pages."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.soboba_casino_resort import SobobaCasinoResortEvent


@dataclass
class SobobaCasinoResortPageData:
    """Raw extracted events from one Soboba calendar page."""

    event_list: List[SobobaCasinoResortEvent]
