"""Data model for a Wix/Velo _functions/shows response item."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class WixFunctionsShowEvent(ShowConvertible):
    """A single show from a custom Wix/Velo _functions/shows endpoint."""

    title: str
    start: datetime
    ticket_url: str
    price_from: Optional[float] = None
    lineup_text: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert the endpoint event to a Show domain object."""
        if self.start is None:
            return None

        show_page_url = url or self.ticket_url
        tickets = []
        if self.ticket_url:
            ticket = ShowFactoryUtils.create_fallback_ticket(self.ticket_url)
            ticket.price = self.price_from
            tickets.append(ticket)

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=self.start,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            description=self.lineup_text,
            room=None,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
