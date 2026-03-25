"""Data model for a single event scraped from the Laugh Factory CMS website via Tixologi ticketing."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# "Wed\xa0Mar 25" → strip weekday prefix + non-breaking space
_DATE_PREFIX_RE = re.compile(r"^\w{3}\xa0")
# "Mar 25" → parse abbreviated month + day
_MONTH_ABBREVS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
_MONTH_DAY_RE = re.compile(r"(\w{3})\s+(\d{1,2})")


def _infer_year(month: int, day: int, tz: str) -> int:
    """Return the nearest future year for the given month/day in the given timezone."""
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
class TixologiEvent(ShowConvertible):
    """
    Data model for a single event from the Laugh Factory CMS website.

    The Laugh Factory CMS renders shows as `.show-sec.jokes` divs.  Each div
    contains a date string (e.g. "Wed\\xa0Mar 25"), a time string (e.g.
    "7:00 PM"), an optional ticket URL, and a list of comedian names.

    The `punchup_id` is embedded in the ticket URL:
      https://www.laughfactory.club/checkout/show/{punchup_id}
    """

    club_id: int
    title: str
    date_str: str       # "Mar 25" (weekday prefix already stripped)
    time_str: str       # "7:00 PM"
    ticket_url: str     # https://www.laughfactory.club/checkout/show/{id}
    timezone: str       # e.g. "America/Los_Angeles"
    comedians: List[str] = field(default_factory=list)
    punchup_id: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a TixologiEvent to a Show domain object."""
        try:
            m = _MONTH_DAY_RE.match(self.date_str.strip())
            if not m:
                return None
            month = _MONTH_ABBREVS.get(m.group(1))
            if month is None:
                return None
            day = int(m.group(2))
            year = _infer_year(month, day, self.timezone)

            # Parse time — "7:00 PM" or "11:00 AM" → 24-hour ISO
            time_dt = datetime.strptime(self.time_str.strip(), "%I:%M %p")
            dt_str = f"{year}-{month:02d}-{day:02d} {time_dt.hour:02d}:{time_dt.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str, self.timezone or club.timezone
            )
        except Exception:
            return None

        show_url = url or self.ticket_url
        tickets = []
        if show_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(show_url, sold_out=False))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=show_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
