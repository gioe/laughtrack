"""Event model for Troy Savings Bank Music Hall's official events page."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class TroySavingsBankMusicHallEvent(ShowConvertible):
    """A single event from Troy Savings Bank Music Hall's rendered event cards."""

    title: str
    date_str: str
    time_str: str
    detail_url: str
    ticket_url: str = ""
    subtitle: str = ""
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert this event into a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.time_str or not self.detail_url:
            return None

        try:
            naive = datetime.strptime(
                f"{self.date_str} {self.time_str}",
                "%b %d %Y %I:%M%p",
            )
        except ValueError:
            return None

        timezone_name = club.timezone or "America/New_York"
        show_date = naive.replace(tzinfo=ZoneInfo(timezone_name))
        ticket_url = url or self.ticket_url or self.detail_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]
        description = self.description or self.subtitle

        show_page_url = self.detail_url if "?" in self.detail_url else f"{self.detail_url}?"

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=show_date,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            description=description,
            supplied_tags=["event", "comedy"],
            enhanced=enhanced,
        )
