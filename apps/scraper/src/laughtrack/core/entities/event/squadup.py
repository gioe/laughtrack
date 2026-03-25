"""Data model for a single event scraped from the SquadUP API."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_GENERIC_TITLE_RE = re.compile(
    r"\b(showcase|comedy show|comedy club|open mic|comedy gold|comedy killers|"
    r"comedy hour|comedy night|sundays|spotlight|drop in|after dark|main course|"
    r"live at sunset|live at the sunset|big texas|deathsquad|secret show|"
    r"comedy strip|improv|roast|battle|episode|best of)\b"
    r"|presents:",
    re.IGNORECASE,
)
_AND_FRIENDS_RE = re.compile(r"\s+and\s+friends?\s*$", re.IGNORECASE)


@dataclass
class SquadUpEvent(ShowConvertible):
    """
    Data model for a single event fetched from the SquadUP API.

    SquadUP (squadup.com) is a ticketing platform used by Sunset Strip
    Comedy Club (Austin, TX). Events are fetched via:
      GET https://www.squadup.com/api/v3/events?user_ids=<user_id>&page_size=100

    The ``start_at`` field is an ISO 8601 string with a UTC offset, e.g.
    ``"2026-03-26T20:00:00-05:00"``. The ticket URL is the ``url`` field,
    e.g. ``"https://squadup.com/events/comedy-gold-51"``.
    """

    event_id: int           # Numeric event ID from SquadUP
    name: str               # Event title, e.g. "Comedy Gold"
    start_at: str           # ISO 8601 with UTC offset, e.g. "2026-03-26T20:00:00-05:00"
    url: str                # SquadUP ticket/event page URL
    timezone_name: str      # IANA timezone, e.g. "America/Chicago"
    performers: List[str] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a SquadUpEvent to a Show domain object."""
        try:
            start_date = datetime.fromisoformat(self.start_at)
        except (ValueError, TypeError):
            return None

        ticket_url = url or self.url
        tickets = []
        if ticket_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(ticket_url))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=ShowFactoryUtils.create_lineup_from_performers(self.performers),
            tickets=tickets,
            description=None,
            room=None,
            supplied_tags=["event"],
            enhanced=enhanced,
        )

    @staticmethod
    def extract_performers(name: str) -> List[str]:
        """
        Derive comedian name(s) from the show title.

        - Generic titles (Showcase, Comedy Show, Secret Show, etc.) → []
        - "[Name] and Friends" → ["[Name]"]
        - Otherwise → [name] (assumed to be comedian's name)
        """
        if _GENERIC_TITLE_RE.search(name):
            return []
        cleaned = _AND_FRIENDS_RE.sub("", name).strip()
        return [cleaned] if cleaned else []
