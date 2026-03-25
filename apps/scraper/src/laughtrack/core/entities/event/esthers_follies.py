"""Data model for a single show slot scraped from Esther's Follies (Austin, TX)."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_TICKET_URL = "https://www.esthersfollies.com/tickets"

_MONTH_NUMS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


@dataclass
class EsthersFolliesEvent(ShowConvertible):
    """
    Data model for a single show slot at Esther's Follies (Austin, TX).

    Esther's Follies is an Austin comedy institution since 1977, performing sketch
    comedy, political satire, and award-winning magic at 525 E. 6th Street.
    Shows run Thursday–Saturday nights. Tickets are sold via VBO Tickets
    (plugin.vbotickets.com); there are no per-show stable ticket URLs.

    Fields map from the VBO date slider HTML:
      edid    ← VBO event date instance ID (unique per show occurrence)
      month   ← abbreviated month name (e.g. "Mar", "Apr")
      day     ← day of month (integer)
      weekday ← abbreviated weekday (e.g. "Thu", "Fri", "Sat")
      time    ← local show time (e.g. "7:00 PM", "9:00 PM")
    """

    edid: str     # VBO event date instance ID
    month: str    # Abbreviated month, e.g. "Mar"
    day: int      # Day of month
    weekday: str  # Abbreviated weekday, e.g. "Thu"
    time: str     # Show time, e.g. "7:00 PM"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this show slot to a Show domain object."""
        try:
            month_num = _MONTH_NUMS.get(self.month.strip())
            if not month_num:
                return None

            today = date.today()
            year = today.year
            show_date = date(year, month_num, self.day)
            if show_date < today:
                year += 1
                show_date = date(year, month_num, self.day)

            time_obj = datetime.strptime(self.time.strip(), "%I:%M %p")
            dt_str = f"{show_date.isoformat()} {time_obj.hour:02d}:{time_obj.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str, club.timezone or "America/Chicago"
            )
        except Exception:
            return None

        ticket_url = url or _TICKET_URL
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name="Esther's Follies",
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description="Sketch Comedy | Political Satire | Award-winning Magic",
            room="Main Room",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
