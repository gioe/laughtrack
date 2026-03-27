"""
Data model for a single event from Zanies Comedy Club.

Show data is extracted from:
- Series pages: /calendar/category/series/{slug}/... — multiple performances
  per headliner run
- Single-show pages: /show/{slug}/... — standalone special events

Both page types provide dates in the format 'Thursday, March 26'
(full weekday + full month + day, no year). Year inference is handled at
parse time.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger


# Regex to pull the show time out of "Doors: 6 pm Show: 7 pm" strings.
_SHOW_TIME_RE = re.compile(r"Show:\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))", re.IGNORECASE)

# Normalise "8 pm" / "9:30 pm" → "8:00 PM" / "9:30 PM"
_TIME_PART_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", re.IGNORECASE)


def _normalize_time(raw: str) -> Optional[str]:
    """Convert '8 pm' or '9:30 pm' to '8:00 PM' / '9:30 PM'."""
    m = _TIME_PART_RE.match(raw.strip())
    if not m:
        return None
    hour = m.group(1)
    minutes = m.group(2) or "00"
    ampm = m.group(3).upper()
    return f"{hour}:{minutes} {ampm}"


def _extract_show_time(time_str: str) -> Optional[str]:
    """
    Pull the show start time from a string like 'Doors: 6 pm Show: 7 pm'.

    Falls back to the whole string if no 'Show:' marker is present.
    """
    m = _SHOW_TIME_RE.search(time_str)
    raw = m.group(1) if m else time_str.strip()
    return _normalize_time(raw)


def _infer_date(date_str: str) -> Optional[date]:
    """
    Parse a date like 'Thursday, March 26' and infer the correct year.

    The listing pages only show upcoming events, so we try the current
    year first.  If that date has already passed (by more than one day)
    we use the following year instead.
    """
    today = date.today()
    for year in (today.year, today.year + 1):
        try:
            parsed = datetime.strptime(f"{date_str} {year}", "%A, %B %d %Y").date()
            if parsed >= today - timedelta(days=1):
                return parsed
        except ValueError:
            continue
    return None


@dataclass
class ZaniesEvent(ShowConvertible):
    """
    A single event scraped from Zanies Comedy Club (Chicago, IL).

    Covers both headliner-run individual performances (extracted from series
    pages) and one-off special events (extracted from single-show detail
    pages).  The date format is 'Thursday, March 26' for both types.
    """

    title: str       # e.g. "Roast Battle Chicago" or "Adam Nate Levine"
    date_str: str    # e.g. "Thursday, March 26"  (no year)
    time_str: str    # e.g. "Doors: 9 pm Show: 9:30 pm"
    ticket_url: str  # e.g. "https://www.etix.com/ticket/p/52372512/..."

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
            Logger.debug(
                f"ZaniesEvent: no parseable show time in {self.time_str!r} "
                f"for '{self.title}' on {self.date_str} — skipping"
            )
            return None

        datetime_str = (
            f"{event_date.year}-{event_date.month:02d}-{event_date.day:02d} {show_time}"
        )
        start_dt = ShowFactoryUtils.safe_parse_datetime_string(
            datetime_str, "%Y-%m-%d %I:%M %p", club.timezone or "America/Chicago"
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
