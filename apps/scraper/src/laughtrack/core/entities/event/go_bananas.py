"""Data model for Go Bananas Comedy Club showtimes."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class GoBananasEvent(ShowConvertible):
    """One ticketed showtime from Go Bananas' custom WordPress show listing."""

    title: str
    date: str
    time: str
    source_url: str
    ticket_url: str
    price: float = 0.0

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            time_obj = datetime.strptime(self.time.strip().upper(), "%I:%M %p")
            dt_str = f"{self.date} {time_obj.hour:02d}:{time_obj.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str,
                club.timezone or "America/New_York",
            )
        except Exception:
            return None

        ticket_url = url or self.ticket_url or self.source_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=self.price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Go Bananas Comedy Club Show",
            club=club,
            date=start_date,
            show_page_url=self.source_url or ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
