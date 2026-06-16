"""Data model for a single show occurrence scraped from The Nest Theatre (Columbus, OH)."""

from dataclasses import dataclass
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# The per-event VBO buy link (plugin.vbotickets.com/v5.0/event.asp?eid=...&s=<session>)
# is session-scoped and non-shareable, so — like Esther's Follies — every show
# points at the stable public shows page instead.
_SHOWS_URL = "https://nesttheatre.com/shows/"


@dataclass
class NestTheatreEvent(ShowConvertible):
    """
    A single dated show occurrence at The Nest Theatre (Columbus, OH), an
    improv + stand-up comedy theatre at 2643 N High St. Tickets are sold via
    VBO Tickets (plugin.vbotickets.com); the extractor parses the embedded
    "showevents" grid, keeps only data-event-category="Live Shows" entries
    (classes/camps/workshops are excluded), and expands recurring listings into
    one event per upcoming date.

    Fields:
      name     ← VBO data-event-name
      dt_str   ← local "YYYY-MM-DD HH:MM:00" computed by the extractor
      room     ← sub-venue/stage (e.g. "Mainstage", "The Birdhouse")
      price    ← lowest advertised ticket price (None if unknown)
    """

    name: str
    dt_str: str
    room: str = ""
    price: Optional[float] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this occurrence to a Show domain object."""
        try:
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                self.dt_str, club.timezone or "America/New_York"
            )
        except Exception:
            return None

        ticket_url = url or _SHOWS_URL
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=self.price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            room=self.room,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
