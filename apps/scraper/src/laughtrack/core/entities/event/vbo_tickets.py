"""Data model for a single event from a VBO Tickets ``ListEvents`` listing.

VBO Tickets (vbotickets.com) is a hosted ticketing platform embedded in a
venue's own site via ``connect.vbotickets.com/_assets/js/plugin.js`` keyed by a
per-venue ``SiteID`` GUID. The plugin renders a multi-event listing by calling
``/Plugin/events/showevents?ViewType=list&EventType=current&s=<session>``; this
entity maps one event row from that listing into a Show. Shared by every venue
onboarded via the generic ``vbo_tickets`` scraper.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# VBO event names frequently carry a trailing " M/D" date suffix (e.g.
# "Macho Mule Comedy Show  6/16"); strip it so the show name is clean.
_TRAILING_DATE_RE = re.compile(r"\s+\d{1,2}/\d{1,2}(/\d{2,4})?\s*$")
# VBO date format on the listing: "Tue, 6/16/2026 @ 7:00 PM".
_VBO_DATE_RE = re.compile(
    r"(?:[A-Za-z]{3,9},\s*)?"  # optional weekday prefix
    r"(\d{1,2}/\d{1,2}/\d{4})\s*@\s*(\d{1,2}:\d{2}\s*[AaPp][Mm])"
)


@dataclass
class VboEvent(ShowConvertible):
    """A single event row from a VBO Tickets ``showevents`` listing."""

    eid: str
    name: str
    date_str: str  # raw VBO date, e.g. "Tue, 6/16/2026 @ 7:00 PM"
    url: str  # stable VBO event-page URL (no session token)
    price_min: Optional[float] = None  # lowest parsed price, if any

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a VboEvent to a Show domain object, or None if unparseable."""
        name = _TRAILING_DATE_RE.sub("", (self.name or "").strip()) or "Comedy Show"

        m = _VBO_DATE_RE.search(self.date_str or "")
        if not m:
            return None
        try:
            naive = datetime.strptime(f"{m.group(1)} {m.group(2).upper().replace(' ', '')}", "%m/%d/%Y %I:%M%p")
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                naive.isoformat(), club.timezone
            )
        except Exception:
            return None

        show_url = url or self.url
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(show_url, price=self.price_min)
        ]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=name,
            club=club,
            date=start_date,
            show_page_url=show_url,
            lineup=[],
            tickets=tickets,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
