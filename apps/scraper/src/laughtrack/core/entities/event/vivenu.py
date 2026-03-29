"""Data model for a single event from a Vivenu-powered ticket seller page."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class VivenuEvent(ShowConvertible):
    """
    Data model for a single event from a Vivenu seller page.

    Vivenu embeds all upcoming events in __NEXT_DATA__ JSON on the seller page:
      props.pageProps.sellerPage.events[]

    Fields map directly from the API response:
      event_id       ← _id (MongoDB ObjectId string)
      name           ← name (event title)
      start_utc      ← start (ISO 8601 UTC timestamp, e.g. "2026-03-29T02:00:47.224Z")
      event_url      ← url (slug for constructing the ticket URL)
      tz             ← timezone (IANA timezone string, e.g. "America/Chicago")
      ticket_base_url ← derived from scraping_url (e.g. "https://tickets.thirdcoastcomedy.club")
    """

    event_id: str
    name: str
    start_utc: str         # ISO 8601 UTC string
    event_url: str         # slug
    tz: str = "America/Chicago"
    ticket_base_url: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a VivenuEvent to a Show domain object."""
        try:
            tz = ZoneInfo(self.tz or club.timezone or "America/Chicago")
            # Parse ISO 8601 UTC string (may end with Z or +00:00)
            start_str = self.start_utc.replace("Z", "+00:00")
            start_utc_dt = datetime.fromisoformat(start_str)
            start_local = start_utc_dt.astimezone(tz)
        except Exception:
            return None

        base = (self.ticket_base_url or "").rstrip("/")
        ticket_url = f"{base}/event/{self.event_url}" if base and self.event_url else ""
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)] if ticket_url else []

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_local,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
