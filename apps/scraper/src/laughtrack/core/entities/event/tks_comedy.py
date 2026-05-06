"""Event model for TK's static Spothopper events page."""

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _parse_event_datetime(
    date_label: str,
    time_label: str,
    timezone_name: str,
    *,
    now: Optional[datetime] = None,
) -> Optional[datetime]:
    """Parse labels like ``May 10`` and ``1 pm`` into a localized datetime."""
    date_match = re.search(
        r"\b("
        + "|".join(_MONTHS)
        + r")\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s*(\d{4}))?",
        date_label,
        re.IGNORECASE,
    )
    time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap]m)\b", time_label, re.IGNORECASE)
    if not date_match or not time_match:
        return None

    reference = now or datetime.now()
    month = _MONTHS[date_match.group(1).lower()]
    day = int(date_match.group(2))
    year = int(date_match.group(3) or reference.year)
    hour = int(time_match.group(1))
    minute = int(time_match.group(2) or 0)
    meridiem = time_match.group(3).lower()

    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    try:
        naive = datetime(year, month, day, hour, minute)
        if date_match.group(3) is None and naive.date() < reference.date():
            naive = naive.replace(year=year + 1)

        return pytz.timezone(timezone_name).localize(naive)
    except Exception:
        return None


@dataclass
class TksComedyEvent(ShowConvertible):
    """One comedy event from TK's public events page."""

    title: str
    date_label: str
    time_label: str
    ticket_url: str
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert the static event block into a Show."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_label or not self.time_label or not self.ticket_url:
            return None

        start_dt = _parse_event_datetime(
            self.date_label,
            self.time_label,
            club.timezone or "America/Chicago",
        )
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            tickets=[ShowFactoryUtils.create_fallback_ticket(ticket_url)],
            description=self.description or None,
            lineup=[],
            enhanced=enhanced,
        )
