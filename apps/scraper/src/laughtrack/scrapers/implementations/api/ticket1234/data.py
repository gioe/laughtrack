"""Data models for the 1234ticket scraper."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.ports.scraping import EventListContainer


@dataclass
class Ticket1234Event(ShowConvertible):
    """One 1234ticket event normalized from the landing-data API."""

    name: str
    start_date: datetime
    show_page_url: str
    ticket_url: str
    price: Optional[float] = None
    performers: List[str] = field(default_factory=list)

    def to_show(self, club: "Club", enhanced: bool = True, url: Optional[str] = None) -> Optional[object]:
        from laughtrack.core.entities.comedian.model import Comedian
        from laughtrack.core.entities.show.model import Show
        from laughtrack.core.entities.ticket.model import Ticket

        lineup = [Comedian(name=p) for p in self.performers] if self.performers else []
        tickets = []
        if self.ticket_url:
            tickets.append(Ticket(
                price=self.price,
                purchase_url=self.ticket_url,
                type="General Admission",
            ))

        return Show(
            name=self.name,
            club_id=club.id,
            date=self.start_date,
            show_page_url=self.show_page_url,
            lineup=lineup,
            tickets=tickets,
            description=None,
            room=None,
            supplied_tags=[],
        )


@dataclass
class Ticket1234PageData(EventListContainer[Ticket1234Event]):
    """Container for events extracted from the 1234ticket landing-data API."""

    event_list: List[Ticket1234Event]
