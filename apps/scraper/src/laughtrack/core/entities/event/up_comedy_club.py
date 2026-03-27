"""
Data model for a single event at UP Comedy Club (The Second City, Chicago).

Show data is sourced in two steps:

  1. GraphQL API on platform.secondcity.com — lists all Chicago shows with
     venue name metadata, allowing UP Comedy Club shows to be identified.
  2. entityResolver API on secondcity.com — per-show detail page containing
     a base64-encoded patronticketData JSON blob with individual performance
     instances (each with a UTC ISO-8601 datetime and Salesforce ticket URL).

patronticketData instance shape (after base64-decode + JSON-parse):
  {
    "name": "Thursday, May 28, 2026, at 7:00 PM",   # human-readable label
    "soldOut": 0,                                     # 0 = available, 1 = sold out
    "purchaseUrl": "https://secondcityus.my.salesforce-sites.com/ticket/#/instances/...",
    "formattedDates": {"ISO8601": "2026-05-29T00:00:00Z"},  # UTC datetime
    "eventName": "The Best of The Second City: Chicago-Style"
  }
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class UPComedyClubEvent(ShowConvertible):
    """A single performance at UP Comedy Club (via Second City platform)."""

    title: str        # e.g. "The Best of The Second City: Chicago Style"
    date_utc: str     # ISO 8601 UTC string, e.g. "2026-05-29T00:00:00Z"
    ticket_url: str   # Salesforce ticket URL for the specific instance
    sold_out: bool    # True when instance.soldOut != 0

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_utc or not self.ticket_url:
            return None

        try:
            # Parse UTC datetime — instances always include a "Z" suffix
            dt_utc = datetime.fromisoformat(self.date_utc.replace("Z", "+00:00"))
            tz = ZoneInfo(club.timezone or "UTC")
            start_dt = dt_utc.astimezone(tz)
        except Exception as exc:
            Logger.debug(
                f"UPComedyClubEvent: failed to parse date {self.date_utc!r} "
                f"for '{self.title}': {exc}"
            )
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
