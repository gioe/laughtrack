"""Page data for the Tempo Tickets scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tempo_tickets import TempoTicketsEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TempoTicketsPageData(EventListContainer[TempoTicketsEvent]):
    """Container for the dated shows extracted from one Tempo event page."""

    event_list: List[TempoTicketsEvent]
