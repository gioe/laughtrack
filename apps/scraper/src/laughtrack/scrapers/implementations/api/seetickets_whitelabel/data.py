"""Page data model for SeeTickets/Eventim whitelabel event cards."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.seetickets_whitelabel import SeeTicketsWhitelabelEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SeeTicketsWhitelabelPageData(EventListContainer[SeeTicketsWhitelabelEvent]):
    event_list: List[SeeTicketsWhitelabelEvent]
