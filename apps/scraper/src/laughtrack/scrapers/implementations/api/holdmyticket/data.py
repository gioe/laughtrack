"""Page data container for the HoldMyTicket platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.holdmyticket import HoldMyTicketEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class HoldMyTicketPageData(EventListContainer[HoldMyTicketEvent]):
    """Raw extracted show data from a HoldMyTicket whitelabel feed."""

    event_list: List[HoldMyTicketEvent]
