"""Data model for a single event scraped from the Comedy Mothership website."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_MONTH_ABBREVS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
_DATE_RE = re.compile(r"\b([A-Z][a-z]{2})\s+(\d{1,2})\b")
_TIME_RE = re.compile(r"(\d{1,2}:\d{2}\s*[AP]M)", re.IGNORECASE)


def _infer_year(month: int, day: int, tz: str) -> int:
    try:
        zone = pytz.timezone(tz)
    except Exception:
        zone = pytz.utc
    now = datetime.now(zone)
    year = now.year
    try:
        candidate = zone.localize(datetime(year, month, day))
    except Exception:
        return year
    if candidate.date() < now.date():
        year += 1
    return year


@dataclass
class ComedyMothershipEvent(ShowConvertible):
    """
    Data model for a single event from the Comedy Mothership website.

    The Comedy Mothership (320 E 6th St, Austin TX) uses a custom Next.js
    site with Vercel hosting. Shows are listed at comedymothership.com/shows
    (server-rendered HTML). Tickets are sold through SquadUP, accessed via
    the show detail page at comedymothership.com/shows/{show_id}.
    """

    show_id: str            # Numeric ID from URL, e.g. "125284"
    title: str              # Show title, e.g. "Lenny Clarke"
    date_str: str           # e.g. "Wednesday, Mar 25"
    time_str: str           # e.g. "7:00 PM - 9:00 PM"
    room: str               # e.g. "FAT MAN" or "LITTLE BOY"
    timezone: str           # "America/Chicago"
    performers: List[str] = field(default_factory=list)
    sold_out: bool = False

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a ComedyMothershipEvent to a Show domain object."""
        try:
            m = _DATE_RE.search(self.date_str)
            if not m:
                return None
            month = _MONTH_ABBREVS.get(m.group(1))
            if month is None:
                return None
            day = int(m.group(2))
            year = _infer_year(month, day, self.timezone or club.timezone)

            time_match = _TIME_RE.search(self.time_str)
            if not time_match:
                return None
            raw_time = time_match.group(1).strip()
            # Ensure space before AM/PM: "7:00PM" → "7:00 PM"
            raw_time = re.sub(r"([AP]M)$", r" \1", raw_time, flags=re.IGNORECASE).strip()
            raw_time = re.sub(r"\s+", " ", raw_time)
            try:
                time_dt = datetime.strptime(raw_time, "%I:%M %p")
            except ValueError:
                return None

            dt_str = f"{year}-{month:02d}-{day:02d} {time_dt.hour:02d}:{time_dt.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str, self.timezone or club.timezone
            )
        except Exception:
            return None

        ticket_url = url or f"https://comedymothership.com/shows/{self.show_id}"
        tickets = []
        if ticket_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(ticket_url, sold_out=self.sold_out))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=ShowFactoryUtils.create_lineup_from_performers(self.performers),
            tickets=tickets,
            description=None,
            room=self.room,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
