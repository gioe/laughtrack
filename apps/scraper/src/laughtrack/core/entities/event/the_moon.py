"""
Data model for a single event from The Moon (Tallahassee, FL).

Show data is extracted from the /events/ listing page on moonevents.com,
which is powered by the rhp-events WordPress plugin.  Tickets are sold
through eTix.  Unlike some rhp-events sites, The Moon's listing page
includes the full year in its date strings (e.g. "Sat, May 30, 2026").
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


# Normalise "8 pm" / "6:30 pm" -> "8:00 PM" / "6:30 PM"
_TIME_PART_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", re.IGNORECASE)

# Extract the bare time from "Door Time Is: 6:30 pm"
_DOOR_TIME_RE = re.compile(
    r"Door\s+Time\s+Is:\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))", re.IGNORECASE
)


def _normalize_time(raw: str) -> Optional[str]:
    """Convert '8 pm' or '6:30 pm' to '8:00 PM' / '6:30 PM'."""
    m = _TIME_PART_RE.match(raw.strip())
    if not m:
        return None
    hour = m.group(1)
    minutes = m.group(2) or "00"
    ampm = m.group(3).upper()
    return f"{hour}:{minutes} {ampm}"


def _extract_door_time(time_str: str) -> Optional[str]:
    """
    Pull the door time from a string like 'Door Time Is: 6:30 pm'.

    Falls back to trying to parse the whole string as a bare time.
    """
    m = _DOOR_TIME_RE.search(time_str)
    raw = m.group(1) if m else time_str.strip()
    return _normalize_time(raw)


def _parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string like 'Sat, May 30, 2026'.

    Tries the full format first (with year), then falls back to the
    short format (no year) with year inference.
    """
    # Strip leading/trailing whitespace and normalise inner whitespace
    cleaned = " ".join(date_str.split())

    # Remove leading weekday prefix: "Sat, May 30, 2026" -> "May 30, 2026"
    if ", " in cleaned:
        cleaned = cleaned.split(", ", 1)[1]

    # Try with year: "May 30, 2026"
    try:
        return datetime.strptime(cleaned, "%b %d, %Y")
    except ValueError:
        pass

    # Try without year (short format): "May 30"
    from datetime import date, timedelta

    today = date.today()
    for year in (today.year, today.year + 1):
        try:
            parsed = datetime.strptime(f"{cleaned} {year}", "%b %d %Y")
            if parsed.date() >= today - timedelta(days=1):
                return parsed
        except ValueError:
            continue

    return None


@dataclass
class TheMoonEvent(ShowConvertible):
    """
    A single event scraped from The Moon's listing page.

    Fields correspond to the rhp-events plugin card rendered
    inside each ``.eventWrapper.rhpSingleEvent`` block.
    """

    title: str        # e.g. "Rob Schneider"
    date_str: str     # e.g. "Sat, May 30, 2026"
    time_str: str     # e.g. "Door Time Is: 6:30 pm"
    ticket_url: str   # e.g. "https://www.etix.com/ticket/p/37927456/..."

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.ticket_url:
            return None

        # --- date ---
        parsed_dt = _parse_date(self.date_str)
        if parsed_dt is None:
            return None

        # --- time ---
        door_time = _extract_door_time(self.time_str) if self.time_str else None
        if door_time:
            datetime_str = (
                f"{parsed_dt.year}-{parsed_dt.month:02d}-{parsed_dt.day:02d} "
                f"{door_time}"
            )
            start_dt = ShowFactoryUtils.safe_parse_datetime_string(
                datetime_str,
                "%Y-%m-%d %I:%M %p",
                club.timezone or "America/New_York",
            )
        else:
            # No time available — use noon as a placeholder
            datetime_str = (
                f"{parsed_dt.year}-{parsed_dt.month:02d}-{parsed_dt.day:02d} "
                "12:00 PM"
            )
            start_dt = ShowFactoryUtils.safe_parse_datetime_string(
                datetime_str,
                "%Y-%m-%d %I:%M %p",
                club.timezone or "America/New_York",
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
