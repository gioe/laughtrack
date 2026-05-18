"""Page data for the generic SellingTicket scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.sellingticket import SellingTicketEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SellingTicketPageData(EventListContainer[SellingTicketEvent]):
    """Raw extracted SellingTicket events."""

    event_list: List[SellingTicketEvent]
