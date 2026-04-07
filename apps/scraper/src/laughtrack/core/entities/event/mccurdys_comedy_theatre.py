"""
Data model for a single event from McCurdy's Comedy Theatre.

Show data is extracted from individual show detail pages at
mccurdyscomedy.com/shows/show.cfm?shoID=<id>.  Each detail page lists one
or more performance dates under a "Performance Dates" sidebar, with
date/time strings in the format "Thursday, April 09 at 7:00 PM" and
ticket links that redirect to Etix (etix.com/ticket/p/<id>).
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger


# Parse "Thursday, April 09 at 7:00 PM" → (weekday, month, day, time, ampm)
_DATETIME_RE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
    r"(\w+)\s+(\d{1,2})\s+at\s+(\d{1,2}:\d{2})\s+(AM|PM)",
    re.IGNORECASE,
)


def _parse_performance(datetime_str: str) -> Optional[tuple]:
    """Parse 'Thursday, April 09 at 7:00 PM' → (date, time_str).

    Returns (date, "7:00 PM") or None if unparseable.  Year is inferred
    from the current date (tries current year first, then next year).
    """
    m = _DATETIME_RE.search(datetime_str)
    if not m:
        return None
    month_name, day_str, time_part, ampm = m.group(1), m.group(2), m.group(3), m.group(4)

    today = date.today()
    for year in (today.year, today.year + 1):
        try:
            parsed = datetime.strptime(f"{month_name} {day_str} {year}", "%B %d %Y").date()
            if parsed >= today - timedelta(days=1):
                return parsed, f"{time_part} {ampm.upper()}"
        except ValueError:
            continue
    return None


@dataclass
class McCurdysEvent(ShowConvertible):
    """A single performance scraped from McCurdy's Comedy Theatre (Sarasota, FL)."""

    title: str       # e.g. "Jamie Lissow"
    date_str: str    # e.g. "Thursday, April 09 at 7:00 PM"
    ticket_url: str  # e.g. "https://www.etix.com/ticket/p/80809268"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.ticket_url:
            return None

        result = _parse_performance(self.date_str)
        if result is None:
            Logger.debug(
                f"McCurdysEvent: unparseable date/time {self.date_str!r} "
                f"for '{self.title}' — skipping"
            )
            return None

        event_date, show_time = result
        datetime_str = (
            f"{event_date.year}-{event_date.month:02d}-{event_date.day:02d} {show_time}"
        )
        start_dt = ShowFactoryUtils.safe_parse_datetime_string(
            datetime_str, "%Y-%m-%d %I:%M %p", club.timezone or "America/New_York"
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
