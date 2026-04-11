"""
Data model for a single event from Dr. Grins Comedy Club (Grand Rapids, MI).

Shows are listed on the Etix venue page at
https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=35455.
Each event card contains microdata (itemprop="startDate") for future shows,
a calendar day div for near-term shows, and ticket links to etix.com.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


_SHOW_TIME_RE = re.compile(
    r"Show\s+at\s+(\d{1,2}:\d{2}\s*[APap][Mm])", re.IGNORECASE
)


@dataclass
class DrGrinsEvent(ShowConvertible):
    """A single event scraped from the Etix venue page for Dr. Grins."""

    title: str          # e.g. "Jay Jurden | *Special Show*"
    start_date: str     # ISO 8601: "2026-04-23T20:00:00-0400" or "2026-04-23"
    time_str: str       # e.g. "Doors at 7:00 PM, Show at 8:00 PM"
    ticket_url: str     # e.g. "https://www.etix.com/ticket/p/99601250/..."

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_date or not self.ticket_url:
            return None

        # Parse ISO date — may include time+offset or just date
        start_dt = self._parse_start_date(club)
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self._clean_title(),
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )

    def _parse_start_date(self, club: Club) -> Optional[datetime]:
        """Parse start_date (ISO with optional offset) and merge show time."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        tz = club.timezone or "America/Detroit"

        # Try full ISO parse (includes time): 2026-04-23T20:00:00-0400
        try:
            dt = datetime.fromisoformat(self.start_date)
            return ShowFactoryUtils.safe_parse_datetime_string(
                dt.strftime("%Y-%m-%d %I:%M %p"),
                "%Y-%m-%d %I:%M %p",
                tz,
            )
        except (ValueError, TypeError):
            pass

        # Date-only fallback: extract show time from time_str
        show_time = self._extract_show_time() or "8:00 PM"
        try:
            date_part = datetime.strptime(self.start_date[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

        datetime_str = f"{date_part.strftime('%Y-%m-%d')} {show_time}"
        return ShowFactoryUtils.safe_parse_datetime_string(
            datetime_str, "%Y-%m-%d %I:%M %p", tz
        )

    def _extract_show_time(self) -> Optional[str]:
        """Extract show start time from 'Doors at X, Show at Y' string."""
        m = _SHOW_TIME_RE.search(self.time_str)
        return m.group(1).strip() if m else None

    def _clean_title(self) -> str:
        """Remove common Etix suffixes like '| *Special Show*'."""
        title = self.title.strip()
        title = re.sub(r"\s*\|\s*\*?Special Show\*?\s*$", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s*\*Special Show\*\s*$", "", title, flags=re.IGNORECASE)
        return title.strip()
