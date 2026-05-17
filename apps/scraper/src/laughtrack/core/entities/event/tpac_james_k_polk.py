"""Event model for TPAC James K. Polk Theater comedy listings."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

_TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", re.IGNORECASE)


def _parse_date(raw: str):
    value = " ".join((raw or "").replace(",", " ").split())
    for fmt in ("%B %d %Y", "%b %d %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_time(raw: str) -> Optional[str]:
    value = " ".join((raw or "").split()).upper().replace(" ", "")
    match = _TIME_RE.match(value)
    if not match:
        return None
    hour = match.group(1)
    minutes = match.group(2) or "00"
    ampm = match.group(3).upper()
    return f"{hour}:{minutes} {ampm}"


@dataclass
class TpacJamesKPolkEvent(ShowConvertible):
    """A single event from TPAC's Polk Theater comedy category."""

    title: str
    detail_url: str
    ticket_url: str = ""
    date_str: str = ""
    time_str: str = ""
    venue: str = ""
    description: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert this TPAC event into a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.detail_url or not self.date_str or not self.time_str:
            return None

        event_date = _parse_date(self.date_str)
        show_time = _normalize_time(self.time_str)
        if event_date is None or show_time is None:
            return None

        start_dt = ShowFactoryUtils.safe_parse_datetime_string(
            f"{event_date:%Y-%m-%d} {show_time}",
            "%Y-%m-%d %I:%M %p",
            club.timezone or "America/Chicago",
        )
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url or self.detail_url
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=self.detail_url,
            lineup=[],
            tickets=[ShowFactoryUtils.create_fallback_ticket(ticket_url)],
            description=self.description,
            enhanced=enhanced,
        )
