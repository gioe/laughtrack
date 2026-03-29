"""
Data model for a single event from The Comedy Corner Underground (Minneapolis, MN).

Show data is scraped from the StageTime platform at:
  https://ccu.stageti.me/

Pipeline:
  Listing page → event slugs → individual event pages (RSC payload) →
  ComedyCornerEvent (one per occurrence) → Show
"""

import pytz

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


def _parse_stagetime_utc(start_time_utc: str, timezone_name: str) -> Optional[datetime]:
    """
    Parse a UTC ISO timestamp from the StageTime RSC payload and localize it.

    Args:
        start_time_utc: UTC ISO string, e.g. "2026-04-04T01:00:00.000Z"
        timezone_name: IANA timezone string, e.g. "America/Chicago"

    Returns:
        Localized datetime or None if parsing fails.
    """
    try:
        # Parse the UTC timestamp
        naive = datetime.strptime(start_time_utc, "%Y-%m-%dT%H:%M:%S.%fZ")
        utc = pytz.utc.localize(naive)
        tz = pytz.timezone(timezone_name)
        return utc.astimezone(tz)
    except Exception:
        return None


@dataclass
class ComedyCornerEvent(ShowConvertible):
    """
    A single show occurrence scraped from The Comedy Corner Underground StageTime page.

    One instance is created per occurrence (date) for multi-date events.
    """

    title: str            # e.g. "Jeremiah Coughlan"
    start_time_utc: str   # e.g. "2026-04-04T01:00:00.000Z"
    timezone: str         # e.g. "America/Chicago"
    ticket_url: str       # e.g. "https://stageti.me/v/ccu/e/jeremiah-coughlan"
    performers: List[str] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_time_utc or not self.ticket_url:
            return None

        tz_name = self.timezone or club.timezone or "America/Chicago"
        start_dt = _parse_stagetime_utc(self.start_time_utc, tz_name)
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        lineup = ShowFactoryUtils.create_lineup_from_performers(self.performers)

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=lineup,
            tickets=tickets,
            enhanced=enhanced,
        )
