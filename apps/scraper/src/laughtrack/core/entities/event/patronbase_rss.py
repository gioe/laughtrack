"""Data model for a single event from a PatronBase RSS feed."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class PatronBaseRssEvent(ShowConvertible):
    """A single event parsed from a PatronBase productions RSS feed."""

    title: str
    start: datetime
    show_page_url: str
    description: str = ""
    venue: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a PatronBase RSS event to a Show domain object."""
        if self.start is None:
            return None

        page_url = url or self.show_page_url
        tickets = []
        if page_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(page_url))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=self.start,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            description=self.description or None,
            room=self.venue or None,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
