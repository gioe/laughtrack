"""Page data for West River Comedy Club TicketTailor events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class WestRiverComedyPageData(EventListContainer[JsonLdEvent]):
    """JSON-LD Event objects extracted from a TicketTailor detail page."""

    event_list: List[JsonLdEvent]
