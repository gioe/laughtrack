"""
Data model for a single event from The Comedy & Magic Club.

Show data is extracted from the /events/ listing page on
thecomedyandmagicclub.com, which is powered by the rhp-events
WordPress plugin.  The listing page provides short-form dates
(e.g. "Thu, Mar 26") so the year is inferred at parse time.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


# Regex to pull the show time out of "Doors: 6:30 pm Show: 8 pm" strings.
_SHOW_TIME_RE = re.compile(r"Show:\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))", re.IGNORECASE)

# Normalise "8 pm" / "6:30 pm" → "8:00 PM" / "6:30 PM"
_TIME_PART_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", re.IGNORECASE)


def _normalize_time(raw: str) -> Optional[str]:
    """Convert '8 pm' or '6:30 pm' to '8:00 PM' / '6:30 PM'."""
    m = _TIME_PART_RE.match(raw.strip())
    if not m:
        return None
    hour = m.group(1)
    minutes = m.group(2) or "00"
    ampm = m.group(3).upper()
    return f"{hour}:{minutes} {ampm}"


def _extract_show_time(time_str: str) -> Optional[str]:
    """
    Pull the show start time from a string like 'Doors: 6:30 pm Show: 8 pm'.

    Falls back to the whole string if no 'Show:' marker is present.
    """
    m = _SHOW_TIME_RE.search(time_str)
    raw = m.group(1) if m else time_str.strip()
    return _normalize_time(raw)


def _infer_date(date_str: str) -> Optional[date]:
    """
    Parse a short date like 'Thu, Mar 26' and infer the correct year.

    The listing page only shows upcoming events, so we try the current
    year first.  If that date has already passed (by more than one day)
    we use the following year instead.
    """
    today = date.today()
    for year in (today.year, today.year + 1):
        try:
            parsed = datetime.strptime(f"{date_str} {year}", "%a, %b %d %Y").date()
            if parsed >= today - timedelta(days=1):
                return parsed
        except ValueError:
            continue
    return None


@dataclass
class ComedyMagicClubEvent(ShowConvertible):
    """
    A single event scraped from The Comedy & Magic Club listing page.

    Fields correspond directly to what the rhp-events plugin renders
    inside each ``.eventWrapper.rhpSingleEvent`` card.
    """

    title: str       # e.g. "10 Comics Show at 8PM"
    date_str: str    # e.g. "Thu, Mar 26"  (no year)
    time_str: str    # e.g. "Doors: 6:30 pm Show: 8 pm"
    ticket_url: str  # e.g. "https://www.etix.com/ticket/p/98994469/..."

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.ticket_url:
            return None

        # --- date ---
        event_date = _infer_date(self.date_str)
        if event_date is None:
            return None

        # --- time ---
        show_time = _extract_show_time(self.time_str)
        if not show_time:
            return None

        datetime_str = f"{event_date.year}-{event_date.month:02d}-{event_date.day:02d} {show_time}"
        start_dt = ShowFactoryUtils.safe_parse_datetime_string(
            datetime_str, "%Y-%m-%d %I:%M %p", club.timezone or "America/Los_Angeles"
        )
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
