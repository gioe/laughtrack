"""Page data for Fox Tucson Theatre."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.fox_tucson_theatre import FoxTucsonTheatreEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class FoxTucsonTheatrePageData(EventListContainer[FoxTucsonTheatreEvent]):
    """Container for Fox Tucson Theatre event cards."""

    event_list: List[FoxTucsonTheatreEvent]
