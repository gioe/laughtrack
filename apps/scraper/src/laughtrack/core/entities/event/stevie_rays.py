"""
Data model for a single event from Stevie Ray's Improv Company (Chanhassen, MN).

Show data is scraped from the Chanhassen Dinner Theatres ticketing page:
  https://tickets.chanhassendt.com/Online/default.asp?BOparam::WScontent::loadArticle::permalink=stevierays

Each event card (div.result-box-item) provides:
- title via div.item-name (always "Stevie Ray's Comedy Cabaret")
- date/time via span.start-date (e.g. "Friday, April 03, 2026 @ 7:30 PM")

No per-event ticket URL is available — the Buy button opens a JS modal with no
href. The listing page URL is used as the ticket/show URL.
"""

import pytz

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


def _parse_stevie_rays_datetime(
    start_date_str: str, timezone_name: str
) -> Optional[datetime]:
    """
    Parse a date/time string like "Friday, April 03, 2026 @ 7:30 PM"
    and localize to *timezone_name*.

    Returns None if parsing fails.
    """
    try:
        start_date_str = start_date_str.strip()
        naive = datetime.strptime(start_date_str, "%A, %B %d, %Y @ %I:%M %p")
        tz = pytz.timezone(timezone_name)
        return tz.localize(naive)
    except Exception:
        return None


@dataclass
class StevieRaysEvent(ShowConvertible):
    """
    A single event scraped from the Stevie Ray's Comedy Cabaret ticketing page.
    """

    title: str          # e.g. "Stevie Ray's Comedy Cabaret"
    start_date_str: str # e.g. "Friday, April 03, 2026 @ 7:30 PM"
    ticket_url: str     # listing page URL (no per-event URLs available)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_date_str or not self.ticket_url:
            return None

        start_dt = _parse_stevie_rays_datetime(
            self.start_date_str, club.timezone or "America/Chicago"
        )
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
