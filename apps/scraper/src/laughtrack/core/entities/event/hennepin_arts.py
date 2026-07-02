"""Event model for Hennepin Arts comedy events."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


def _parse_local_datetime(value: str, timezone_name: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None

    tz = pytz.timezone(timezone_name or "America/Chicago")
    if parsed.tzinfo is None:
        return tz.localize(parsed)
    return parsed.astimezone(tz)


@dataclass
class HennepinArtsEvent(ShowConvertible):
    """A single Hennepin Arts performance."""

    title: str
    start_date: str
    show_page_url: str
    ticket_url: Optional[str] = None
    venue: str = ""
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        if not self.title or not self.start_date or not self.show_page_url:
            return None

        start_dt = _parse_local_datetime(self.start_date, club.timezone or "America/Chicago")
        if start_dt is None or start_dt < datetime.now(timezone.utc):
            return None

        show_page_url = url or self.show_page_url
        purchase_url = self.ticket_url or show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(purchase_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            description=self.description or None,
            room=self.venue,
            supplied_tags=["event", "comedy"],
            enhanced=enhanced,
        )
