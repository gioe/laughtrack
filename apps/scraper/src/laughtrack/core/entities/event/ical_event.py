"""Data model for a single event parsed from an iCalendar (ICS) feed."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class IcalEvent(ShowConvertible):
    """
    A single VEVENT parsed from an iCalendar feed (RFC 5545).

    Used by the generic ``ical`` scraper, which fetches a public ICS URL such
    as a Google Calendar feed
    (``https://calendar.google.com/calendar/ical/<id>/public/basic.ics``).
    ``start`` is already a timezone-aware datetime resolved by the extractor
    (UTC ``Z`` stamps, ``TZID`` params, and floating/date-only values are all
    localized there using the club timezone), so ``to_show`` just builds the
    Show.
    """

    uid: str
    summary: str
    start: datetime                 # timezone-aware
    show_page_url: str              # event URL, or the venue calendar page
    description: Optional[str] = None
    location: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert an IcalEvent to a Show domain object."""
        if self.start is None:
            return None

        page_url = url or self.show_page_url
        tickets = []
        if page_url:
            # ICS feeds carry no price/ticket field; emit one access-record
            # ticket pointing at the calendar/event page (price unknown).
            tickets.append(ShowFactoryUtils.create_fallback_ticket(page_url))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.summary or "Comedy Show",
            club=club,
            date=self.start,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            description=self.description or None,
            room=None,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
