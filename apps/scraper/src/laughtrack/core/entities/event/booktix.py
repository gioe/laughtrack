"""
Data model for a single BookTix box-office event showtime.

BookTix (booktix.com) hosts a per-organization box office at
``https://{org}.booktix.com``. The box office home (``/dept/main``) lists each
production by event code; every production page
(``/dept/main/e/{code}``) is server-rendered HTML with one or more showtimes,
e.g. "Sat Jun 20 2026 - 7:00 PM". One ``BookTixEvent`` is produced per
showtime — the production name is shared across its showtimes.
"""

import pytz

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

# BookTix showtime format, e.g. "Sat Jun 20 2026 - 7:00 PM"
_BOOKTIX_DT_FORMAT = "%a %b %d %Y - %I:%M %p"


def _parse_booktix_datetime(start_date_str: str, timezone_name: str) -> Optional[datetime]:
    """Parse "Sat Jun 20 2026 - 7:00 PM" and localize to *timezone_name*.

    Returns None if parsing fails.
    """
    try:
        naive = datetime.strptime(start_date_str.strip(), _BOOKTIX_DT_FORMAT)
        return pytz.timezone(timezone_name).localize(naive)
    except Exception:
        return None


@dataclass
class BookTixEvent(ShowConvertible):
    """A single showtime scraped from a BookTix production page."""

    title: str            # e.g. "Point of No Return Improv Comedy"
    start_date_str: str   # e.g. "Sat Jun 20 2026 - 7:00 PM"
    ticket_url: str       # the BookTix production page URL
    price: Optional[float] = None  # GA price in dollars, when present

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are missing."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_date_str or not self.ticket_url:
            return None

        start_dt = _parse_booktix_datetime(
            self.start_date_str, club.timezone or "America/New_York"
        )
        if start_dt is None:
            return None

        # BookTix production pages list every showtime, including ones that have
        # already passed (e.g. a multi-weekend run mid-season). Skip past
        # showtimes so we don't persist stale shows.
        if start_dt < datetime.now(timezone.utc):
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=self.price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
