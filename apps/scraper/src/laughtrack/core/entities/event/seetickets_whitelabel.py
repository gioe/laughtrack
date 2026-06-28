"""Event model for SeeTickets/Eventim whitelabel storefront cards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class SeeTicketsWhitelabelEvent(ShowConvertible):
    event_id: str
    name: str
    start_date: str
    ticket_url: str
    location: str = ""
    image_url: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: str | None = None):
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.name or not self.start_date or not self.ticket_url:
            return None

        try:
            parsed = datetime.strptime(self.start_date, "%B %d %Y")
        except ValueError:
            return None

        try:
            tz = ZoneInfo(club.timezone or "America/New_York")
        except Exception:
            tz = ZoneInfo("America/New_York")
        show_date = parsed.replace(tzinfo=tz)
        tickets = [ShowFactoryUtils.create_fallback_ticket(self.ticket_url)]
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=show_date,
            show_page_url=url or self.ticket_url,
            tickets=tickets,
            enhanced=enhanced,
        )
