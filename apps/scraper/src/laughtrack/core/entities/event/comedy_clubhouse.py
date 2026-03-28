"""
Data model for a single event from The Comedy Clubhouse (Chicago).

Show data is scraped from the TicketSource listing page at:
  https://www.ticketsource.com/thecomedyclubhouse

Each event card (div.eventRow) provides:
- title via span[itemprop="name"] inside div.eventTitle
- ISO start datetime via div.dateTime[content] attribute (e.g. "2026-03-28T19:30")
- show page URL via div.eventTitle > a[href]  (relative, base=ticketsource.com)
- ticket purchase URL via div.event-btn > a[href] (relative, base=ticketsource.com)
"""

import pytz

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

TICKETSOURCE_BASE = "https://www.ticketsource.com"


def _parse_iso_local(dt_str: str, timezone_name: str) -> Optional[datetime]:
    """
    Parse a TicketSource ISO datetime string (e.g. "2026-03-28T19:30") and
    localise it to *timezone_name*.

    Returns None if parsing fails.
    """
    try:
        naive = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M")
        tz = pytz.timezone(timezone_name)
        return tz.localize(naive)
    except Exception:
        return None


@dataclass
class ComedyClubhouseEvent(ShowConvertible):
    """
    A single event scraped from The Comedy Clubhouse TicketSource page.

    Fields correspond directly to what is extracted from each div.eventRow card.
    """

    title: str          # e.g. "MAIN STAGE Improv Showcase"
    start_iso: str      # e.g. "2026-03-28T19:30"  (from content= attribute)
    show_url: str       # e.g. "https://www.ticketsource.com/thecomedyclubhouse/…/e-pdapmv"
    ticket_url: str     # e.g. "https://www.ticketsource.com/booking/init/FMIEDGE"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_iso or not self.ticket_url:
            return None

        start_dt = _parse_iso_local(self.start_iso, club.timezone or "America/Chicago")
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=self.show_url or ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
