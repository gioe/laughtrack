"""Data container for events scraped from a Salesforce PatronTicket site."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.patron_ticket import PatronTicketEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class PatronTicketPageData(EventListContainer[PatronTicketEvent]):
    """Container for PatronTicketEvent objects extracted from the PatronTicket API."""

    event_list: List[PatronTicketEvent]
