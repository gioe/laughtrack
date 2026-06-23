"""Page data for the TicketSpice scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ticketspice import TicketSpiceEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TicketSpicePageData(EventListContainer[TicketSpiceEvent]):
    """Container for the show(s) parsed from one TicketSpice form page."""

    event_list: List[TicketSpiceEvent]
