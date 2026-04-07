"""Data model for a single show from Flappers Comedy Club."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

_TIME_RE = re.compile(r"(\d{1,2}(?::\d{2})?)\s*(AM|PM)", re.IGNORECASE)


def _parse_time(time_str: str, year: int, month: int, day: int, tz_str: str) -> Optional[datetime]:
    """Parse a time string like '7:30PM' into a timezone-aware datetime."""
    m = _TIME_RE.search(time_str)
    if not m:
        return None
    raw, ampm = m.group(1), m.group(2).upper()
    if ":" in raw:
        hour, minute = int(raw.split(":")[0]), int(raw.split(":")[1])
    else:
        hour, minute = int(raw), 0
    if ampm == "PM" and hour != 12:
        hour += 12
    elif ampm == "AM" and hour == 12:
        hour = 0

    from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

    iso = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00"
    return ShowFactoryUtils.parse_datetime_with_timezone_fallback(
        iso, tz_str, "America/Los_Angeles"
    )


@dataclass
class FlappersEvent(ShowConvertible):
    """A single show scraped from flapperscomedy.com calendar."""

    title: str
    event_id: str
    year: int
    month: int
    day: int
    time_str: str
    timezone: str = "America/Los_Angeles"
    room: str = ""

    def to_show(self, club: "Club", enhanced: bool = True, url: Optional[str] = None):
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.time_str:
            return None

        start_date = _parse_time(
            self.time_str, self.year, self.month, self.day, self.timezone
        )
        if not start_date:
            return None

        ticket_url = url or f"https://www.flapperscomedy.com/site/shows.php?event_id={self.event_id}"
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            tickets=tickets,
            room=self.room,
            enhanced=enhanced,
        )
