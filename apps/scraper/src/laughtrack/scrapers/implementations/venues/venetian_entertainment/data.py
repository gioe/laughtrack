"""Page data for Venetian entertainment."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.venetian_entertainment import VenetianEntertainmentEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class VenetianEntertainmentPageData(EventListContainer[VenetianEntertainmentEvent]):
    """Raw extracted Venetian entertainment events."""

    event_list: List[VenetianEntertainmentEvent]
