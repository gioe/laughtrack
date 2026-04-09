"""
Data model for a single event from Comedy Club Haug (Rotterdam, Netherlands).

Show data is scraped from the club's Next.js website at:
  https://comedyclubhaug.com/shows

The site uses Craft CMS with a Next.js frontend. All event data is embedded in
the initial HTML as React Server Components (RSC) streaming payload containing a
`shows` array with rich event objects including artist lineups and Stager ticket
links.

Pipeline:
  /shows page → RSC payload → shows array → ComedyClubHaugEvent → Show
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


def _parse_iso_datetime(iso_str: str, timezone_name: str) -> Optional[datetime]:
    """
    Parse an ISO datetime string and localize to the venue timezone.

    The Craft CMS API returns times with UTC offset (e.g. "2026-04-09T17:30:00+00:00").

    Args:
        iso_str: ISO 8601 datetime string with timezone offset.
        timezone_name: IANA timezone for display (e.g. "Europe/Amsterdam").

    Returns:
        Localized datetime or None if parsing fails.
    """
    try:
        # Python 3.7+ fromisoformat handles +00:00 offset
        dt = datetime.fromisoformat(iso_str)
        tz = pytz.timezone(timezone_name)
        return dt.astimezone(tz)
    except Exception:
        return None


@dataclass
class ComedyClubHaugEvent(ShowConvertible):
    """
    A single show event from Comedy Club Haug.

    Each event corresponds to one show at a specific date/time.
    """

    title: str                  # e.g. "Best of Stand-Up"
    subtitle: str               # e.g. "MC Hidde van Gestel, Theo Maassen..."
    start_time: str             # ISO 8601 e.g. "2026-04-09T18:30:00+00:00"
    end_time: str               # ISO 8601 e.g. "2026-04-09T20:30:00+00:00"
    ticket_url: str             # Stager URL
    show_page_url: str          # comedyclubhaug.com show page URL
    performers: List[str] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_time:
            return None

        tz_name = club.timezone or "Europe/Amsterdam"
        start_dt = _parse_iso_datetime(self.start_time, tz_name)
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url or self.show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)] if ticket_url else []

        lineup = ShowFactoryUtils.create_lineup_from_performers(self.performers)

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=self.show_page_url or ticket_url,
            lineup=lineup,
            tickets=tickets,
            enhanced=enhanced,
        )
