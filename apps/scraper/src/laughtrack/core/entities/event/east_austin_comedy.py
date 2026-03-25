"""Data model for a single show slot scraped from the East Austin Comedy website."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_TICKET_URL = "https://eastaustincomedy.com/#shows"


@dataclass
class EastAustinComedyEvent(ShowConvertible):
    """
    Data model for a single show slot at East Austin Comedy (Austin, TX).

    East Austin Comedy is an intimate 82-seat BYOB comedy room at 2505 E 6th St,
    Austin TX. Shows run nightly and are booked via a Square embedded modal on the
    venue homepage — there are no per-show ticket URLs.

    Comedian lineups are not published on the website; shows are listed generically
    as "Live Stand-Up Comedy".

    Field mapping from Netlify availability API:
      date  ← outer key in API response (e.g. "2026-03-27")
      time  ← inner key within the date (e.g. "6:00 PM")
    """

    date: str   # ISO date string, e.g. "2026-03-27"
    time: str   # Local time string, e.g. "6:00 PM"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this show slot to a Show domain object."""
        try:
            time_obj = datetime.strptime(self.time.strip(), "%I:%M %p")
            dt_str = f"{self.date} {time_obj.hour:02d}:{time_obj.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str, club.timezone or "America/Chicago"
            )
        except Exception:
            return None

        ticket_url = url or _TICKET_URL
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name="Live Stand-Up Comedy",
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room="Main Room",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
