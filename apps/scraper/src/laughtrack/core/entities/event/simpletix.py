"""Data model for SimpleTix events parsed from event pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.core.entities.club.model import Club


@dataclass
class SimpleTixEvent(ShowConvertible):
    """Event parsed from a SimpleTix event page timeArray entry."""

    name: str
    start_date: datetime
    show_page_url: str
    ticket_url: str
    price: Optional[float] = None
    sold_out: bool = False
    performers: List[str] = field(default_factory=list)

    def to_show(self, club: "Club", enhanced: bool = True, url: Optional[str] = None) -> Optional[object]:
        from laughtrack.core.entities.comedian.model import Comedian
        from laughtrack.core.entities.ticket.model import Ticket
        from laughtrack.core.entities.show.model import Show

        lineup = [Comedian(name=p) for p in self.performers] if self.performers else []

        tickets = []
        if self.ticket_url:
            tickets.append(Ticket(
                price=self.price,
                purchase_url=self.ticket_url,
                sold_out=self.sold_out,
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
