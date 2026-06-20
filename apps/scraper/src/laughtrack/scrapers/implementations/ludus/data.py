"""Page data for the Ludus scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ludus import LudusEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class LudusPageData(EventListContainer[LudusEvent]):
    """Container for the dated showtimes extracted from one Ludus detail page."""

    event_list: List[LudusEvent]
