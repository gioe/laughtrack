"""Event model for SellingTicket HTML list pages."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class SellingTicketEvent(ShowConvertible):
    """Single row from a SellingTicket event list."""

    title: str
    address: str
    weekday: str
    date_time: str
    ticket_url: str
    source_url: str

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert the SellingTicket row to a Show."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_time or not self.ticket_url:
            return None

        try:
            naive = datetime.strptime(self.date_time, "%m/%d/%Y %I:%M:%S %p")
        except ValueError:
            return None

        timezone_name = club.timezone or "America/New_York"
        show_date = naive.replace(tzinfo=ZoneInfo(timezone_name))
        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=show_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description="",
            supplied_tags=["event", "comedy"],
            enhanced=enhanced,
        )
