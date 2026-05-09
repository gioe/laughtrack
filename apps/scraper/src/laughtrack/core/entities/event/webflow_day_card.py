"""Event model for Webflow day-card venues with Tixr ticket links."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class WebflowDayCardEvent(ShowConvertible):
    """One Webflow ``a.day-card`` event whose ticket URL points at Tixr."""

    title: str
    date: str
    time: str
    ticket_url: str
    source_url: str
    room: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            time_obj = datetime.strptime(self.time.strip().upper(), "%I:%M %p")
            dt_str = f"{self.date} {time_obj.hour:02d}:{time_obj.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str,
                club.timezone or "UTC",
            )
        except Exception:
            return None

        ticket_url = url or self.ticket_url or self.source_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            enhanced=enhanced,
            room=self.room,
        )
