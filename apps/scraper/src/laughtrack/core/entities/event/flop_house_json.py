"""Data model for a single event from Flop House JSON feeds."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class FlopHouseJsonEvent(ShowConvertible):
    """A single event from Flop House's static JSON feeds."""

    title: str
    start_ms: int
    show_page_url: str
    description: str = ""
    venue_name: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a Flop House JSON event to a Show domain object."""
        try:
            tz = ZoneInfo(club.timezone or "UTC")
            start = datetime.fromtimestamp(self.start_ms / 1000, tz=tz)
        except Exception:
            return None

        page_url = url or self.show_page_url
        tickets = []
        if page_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(page_url))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            description=self.description or None,
            room=self.venue_name or None,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
