"""Venetian entertainment event model."""

from dataclasses import dataclass
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class VenetianEntertainmentEvent(ShowConvertible):
    """A comedy performance from Venetian's AEM entertainment feed."""

    name: str
    start_date: str
    show_page_url: str
    ticket_url: str
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            parsed_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                self.start_date, club.timezone or "America/Los_Angeles"
            )
        except Exception:
            return None

        page_url = url or self.show_page_url
        ticket_url = self.ticket_url or page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)] if ticket_url else []

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=parsed_date,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event", "comedy"],
            description=self.description or None,
            enhanced=enhanced,
        )
