"""Data model for one dated Ticket Tailor show instance.

Ticket Tailor box-office listings (tickettailor.com/events/<account>/) are sold
by a single account that may be a roving producer running shows at varying
physical venues. Each event therefore carries its OWN venue (name + zip), which
the scraper resolves into a per-venue club; this event converts to a Show on
that venue club. The buy URL is the event detail page.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class TicketTailorEvent(ShowConvertible):
    """One Ticket Tailor event with its own (roving) venue."""

    title: str
    # Naive local start datetime parsed from the listing.
    start: datetime
    event_url: str
    venue_name: str
    venue_zip: str = ""
    # IANA timezone inferred from the listing's timezone abbreviation; falls
    # back to the resolved venue club's timezone.
    timezone: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
            self.start.strftime("%Y-%m-%d %H:%M:%S"),
            self.timezone or club.timezone or "America/Chicago",
        )

        source_url = url or self.event_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(source_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or club.name,
            club=club,
            date=start_date,
            show_page_url=source_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
