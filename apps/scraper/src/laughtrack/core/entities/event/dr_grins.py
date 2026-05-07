"""Event model for Dr. Grins Comedy Club's public BOB pages."""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

_TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", re.IGNORECASE)


def _normalize_time(raw: str) -> Optional[str]:
    """Normalize compact public-page times like ``8pm`` to ``8:00 PM``."""
    match = _TIME_RE.match(" ".join((raw or "").split()))
    if not match:
        return None
    hour = match.group(1)
    minutes = match.group(2) or "00"
    ampm = match.group(3).upper()
    return f"{hour}:{minutes} {ampm}"


def _infer_date(month_day: str) -> Optional[date]:
    """Infer the year for a public Dr. Grins date like ``May 8``."""
    today = date.today()
    for year in (today.year, today.year + 1):
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                parsed = datetime.strptime(f"{month_day} {year}", fmt).date()
            except ValueError:
                continue
            if parsed >= today - timedelta(days=1):
                return parsed
    return None


@dataclass
class DrGrinsEvent(ShowConvertible):
    """A single Dr. Grins performance from a public comedian detail page."""

    title: str
    date_str: str
    time_str: str
    detail_url: str
    ticket_url: str

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.time_str:
            return None

        event_date = _infer_date(self.date_str)
        show_time = _normalize_time(self.time_str)
        if event_date is None or show_time is None:
            return None

        start_dt = ShowFactoryUtils.safe_parse_datetime_string(
            f"{event_date:%Y-%m-%d} {show_time}",
            "%Y-%m-%d %I:%M %p",
            club.timezone or "America/Detroit",
        )
        if start_dt is None:
            return None

        ticket_url = self.ticket_url or self.detail_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=self.detail_url or ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
