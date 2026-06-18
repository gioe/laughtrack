"""Data model for scraped page data from The Comedy Clubhouse."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_clubhouse import ComedyClubhouseEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComedyClubhousePageData(EventListContainer[ComedyClubhouseEvent]):
    """Raw extracted event data from The Comedy Clubhouse TicketSource page."""

    event_list: List[ComedyClubhouseEvent]
