"""Data model for a single event from The Setup (Google Sheets CSV)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


# Time formats accepted from the CSV's `time` column, tried in order.
# Handles standard "9:00 PM", compact "9PM" / "9 PM", and 24-hour "21:00".
_TIME_FMTS = [
    "%I:%M %p",   # "9:00 PM"  (canonical Google Sheets format)
    "%I:%M%p",    # "9:00PM"
    "%I %p",      # "9 PM"
    "%I%p",       # "9PM"
    "%H:%M",      # "21:00"
]


@dataclass
class SetupEvent(ShowConvertible):
    """
    Data model for a single event from The Setup's Google Sheets CSV calendar.

    Each city location publishes a separate tab (gid) in the same Google Sheet.
    The club's scraping_url encodes the city-specific gid.

    CSV columns: date,day,time,title,venue,city,ticket_url,urgency_tag,sold_out

    Fields:
      date       ← date column (YYYY-MM-DD)
      time       ← time column (e.g. "9:00 PM", "9PM")
      title      ← title column
      venue      ← venue column (e.g. "The Palace Theater", "The Lost Church")
      ticket_url ← ticket_url column (Squarespace product page URL)
      sold_out   ← sold_out column (truthy string = sold out)
    """

    date: str        # "YYYY-MM-DD"
    time: str        # "9:00 PM" / "9PM" / "21:00"
    title: str
    venue: str
    ticket_url: str
    sold_out: bool = False

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a SetupEvent to a Show domain object."""
        try:
            tz = ZoneInfo(club.timezone or "America/Los_Angeles")
            naive = None
            for fmt in _TIME_FMTS:
                try:
                    naive = datetime.strptime(f"{self.date} {self.time}", f"%Y-%m-%d {fmt}")
                    break
                except ValueError:
                    continue
            if naive is None:
                return None
            start_date = naive.replace(tzinfo=tz, fold=0)  # fold=0: first occurrence during DST fall-back
        except Exception:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, sold_out=self.sold_out)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room=self.venue,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
