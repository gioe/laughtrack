"""Event model for Soboba Casino Resort's public entertainment calendar."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

_TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", re.IGNORECASE)


def _normalize_time(raw: str) -> Optional[str]:
    """Normalize compact or spaced times to ``H:MM AM/PM``."""
    match = _TIME_RE.match(" ".join((raw or "").split()))
    if not match:
        return None
    hour = match.group(1)
    minutes = match.group(2) or "00"
    ampm = match.group(3).upper()
    return f"{hour}:{minutes} {ampm}"


def _parse_date(raw: str):
    """Parse Soboba listing dates like ``Jun 13, 2026``."""
    value = " ".join((raw or "").split())
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class SobobaCasinoResortEvent(ShowConvertible):
    """A single event from Soboba Casino Resort's public calendar."""

    title: str
    date_str: str
    time_str: str
    room: str
    detail_url: str
    ticket_url: str = ""
    description: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert this calendar event into a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.time_str or not self.detail_url:
            return None

        event_date = _parse_date(self.date_str)
        show_time = _normalize_time(self.time_str)
        if event_date is None or show_time is None:
            return None

        start_dt = ShowFactoryUtils.safe_parse_datetime_string(
            f"{event_date:%Y-%m-%d} {show_time}",
            "%Y-%m-%d %I:%M %p",
            club.timezone or "America/Los_Angeles",
        )
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url or self.detail_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=self.detail_url,
            lineup=[],
            tickets=tickets,
            description=self.description,
            room=self.room,
            enhanced=enhanced,
        )
