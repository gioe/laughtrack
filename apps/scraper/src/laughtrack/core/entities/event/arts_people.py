"""Data model for a single Arts-People (Neon One) performance.

Venues running on Arts-People publish a public ticketing page at
``https://app.arts-people.com/index.php?ticketing={shortName}`` listing each
current production, plus a per-show page at ``?show={id}`` whose
``TBLperformances`` table renders one bookable performance per date as a link
like ``Sat, Jul 11th, 2026 at 7:30 pm``. One ``ArtsPeopleEvent`` is produced per
performance, sharing the production title and stable ``?show={id}`` detail URL.
"""

import re

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

# Performance link text, e.g. "Sat, Jul 11th, 2026 at 7:30 pm" — the leading
# weekday and the day ordinal suffix are both optional/stripped.
_PERFORMANCE_DT_RE = re.compile(
    r"(?:[A-Za-z]+,\s*)?"            # optional "Sat, "
    r"([A-Za-z]{3,})\s+"            # month name (abbrev or full)
    r"(\d{1,2})(?:st|nd|rd|th)?,\s*"  # day, optional ordinal suffix
    r"(\d{4})\s+at\s+"             # year
    r"(\d{1,2}):(\d{2})\s*"         # H:MM
    r"([APap][Mm])",               # am/pm
)


def _parse_performance_datetime(date_str: str, timezone_name: str) -> Optional[datetime]:
    """Parse an Arts-People performance string and localize it.

    Handles the optional weekday prefix, the day ordinal suffix, and both
    abbreviated ("Jul") and full ("July") month names. Returns None if the
    string does not match or the timezone is unknown.
    """
    m = _PERFORMANCE_DT_RE.search(date_str or "")
    if not m:
        return None
    month, day, year, hour, minute, meridiem = m.groups()
    normalized = f"{month} {day} {year} {hour}:{minute} {meridiem.upper()}"
    naive: Optional[datetime] = None
    for fmt in ("%b %d %Y %I:%M %p", "%B %d %Y %I:%M %p"):
        try:
            naive = datetime.strptime(normalized, fmt)
            break
        except ValueError:
            continue
    if naive is None:
        return None
    try:
        return pytz.timezone(timezone_name).localize(naive)
    except pytz.UnknownTimeZoneError:
        return None


@dataclass
class ArtsPeopleEvent(ShowConvertible):
    """A single bookable performance scraped from an Arts-People ``?show={id}`` page."""

    title: str          # production name, e.g. "Front deRanged Improv Comedy"
    date_str: str       # performance link text, e.g. "Sat, Jul 11th, 2026 at 7:30 pm"
    show_page_url: str  # the stable ?show={id} detail/booking page

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show, or None if required fields are missing, the date is
        unparseable, or the performance is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.show_page_url:
            return None

        start_dt = _parse_performance_datetime(
            self.date_str, club.timezone or "America/Denver"
        )
        if start_dt is None:
            return None

        if start_dt < datetime.now(timezone.utc):
            return None

        show_page_url = url or self.show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(show_page_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
