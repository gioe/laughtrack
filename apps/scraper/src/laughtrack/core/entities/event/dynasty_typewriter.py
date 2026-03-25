"""Data model for a single event from Dynasty Typewriter's SquadUp API."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class DynastyTypewriterEvent(ShowConvertible):
    """
    Data model for a single event from Dynasty Typewriter's SquadUp API.

    The API endpoint is:
      https://www.squadup.com/api/v3/events?user_ids=7408591

    Fields map directly from the API response.
    """

    id: str
    title: str
    start_at: str  # ISO 8601 with tz offset, e.g. "2026-03-13T19:30:00-07:00"
    url: str  # SquadUp event page URL (also the ticket URL)
    timezone_name: str = "America/Los_Angeles"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a DynastyTypewriterEvent to a Show domain object."""
        try:
            tz = ZoneInfo(self.timezone_name or club.timezone or "America/Los_Angeles")
            start_date = datetime.fromisoformat(self.start_at).astimezone(tz)
        except Exception:
            return None

        ticket_url = url or self.url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
