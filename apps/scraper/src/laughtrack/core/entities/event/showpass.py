"""
Data model for a single event from the Showpass public calendar API.

Comedy Cave (Calgary, AB) uses a Showpass embedded widget.  Upcoming shows are
available via the public calendar endpoint:

  GET https://www.showpass.com/api/public/venues/{slug}/calendar/
      ?venue__in={venue_id}&only_parents=true&page_size=100
      &ends_on__gte={start}&starts_on__lt={end}

Each item in the ``results`` array represents one show with title, dates
(ISO 8601 with UTC offset), slug (for ticket URL), and sold-out status.

Comedian names are extracted from the event ``name`` field, which typically
follows the pattern "Performing <date> : <Comedian Name>".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


_NAME_RE = re.compile(r"^Performing\s+\w+\s+\d{1,2}\s*:\s*(.+)$", re.IGNORECASE)


@dataclass
class ShowpassEvent(ShowConvertible):
    """A single Showpass calendar event."""

    event_id: int
    name: str
    slug: str
    starts_on: str          # ISO 8601 e.g. "2026-04-14T01:30:00+00:00"
    ends_on: str
    timezone: str            # IANA e.g. "America/Edmonton"
    sold_out: bool = False
    status: str = ""
    description: str = ""

    @classmethod
    def from_api_response(cls, data: dict) -> ShowpassEvent:
        """Create a ShowpassEvent from a Showpass calendar API dict."""
        return cls(
            event_id=int(data.get("id", 0)),
            name=(data.get("name") or "").strip(),
            slug=(data.get("slug") or "").strip(),
            starts_on=data.get("starts_on") or "",
            ends_on=data.get("ends_on") or "",
            timezone=data.get("timezone") or "",
            sold_out=bool(data.get("sold_out", False)),
            status=data.get("status") or "",
            description=data.get("description") or "",
        )

    def _extract_comedian_name(self) -> str:
        """Extract comedian name from the event title.

        Handles patterns like:
          "Performing April 13 : Tre Stewart" -> "Tre Stewart"
          "Sunday Smoke Show" -> "" (no comedian)
          "The Workshop" -> "" (no comedian)
        """
        m = _NAME_RE.match(self.name)
        return m.group(1).strip() if m else ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show object."""
        from laughtrack.core.entities.comedian.model import Comedian
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.name or not self.starts_on:
            return None

        try:
            start_date = datetime.fromisoformat(self.starts_on)
        except ValueError:
            return None

        ticket_url = f"https://www.showpass.com/{self.slug}/"
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, sold_out=self.sold_out)]

        # Use the club's shows page as show_page_url (drives traffic to venue)
        show_page_url = url or (club.scraping_url or club.website or ticket_url)

        lineup = []
        comedian_name = self._extract_comedian_name()
        if comedian_name:
            lineup = [Comedian(name=comedian_name)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=lineup,
            tickets=tickets,
            enhanced=enhanced,
        )
