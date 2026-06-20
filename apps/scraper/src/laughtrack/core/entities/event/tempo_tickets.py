"""Data model for one dated Tempo Tickets show instance.

A Tempo "event" (e.g. ``2026 ComedySportz Friday 7:30 Match``) is a *recurring*
listing; each upcoming individual performance is an ``<option>`` in the event
page's ``<select name='EventDateID'>``. The extractor fans those options out
into one :class:`TempoTicketsEvent` per upcoming date, which converts to a Show
here. The buy URL is the event page (the EventDateID is passable downstream).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class TempoTicketsEvent(ShowConvertible):
    """One upcoming dated performance parsed from a Tempo event page."""

    title: str
    # Already resolved to an absolute datetime by the extractor (year inferred
    # from the current-date rollover, since Tempo option text carries no year).
    start: datetime
    event_url: str
    date_id: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
            self.start.strftime("%Y-%m-%d %H:%M:%S"),
            club.timezone or "America/Chicago",
        )

        source_url = url or self.event_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(source_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "ComedySportz Match",
            club=club,
            date=start_date,
            show_page_url=source_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event", "improv"],
            enhanced=enhanced,
        )
