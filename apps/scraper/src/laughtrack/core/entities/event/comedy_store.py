"""
Data model for a single show from The Comedy Store.

Show data is extracted from the day-by-day HTML calendar at
thecomedystore.com/calendar/YYYY-MM-DD.  Each show item provides:
  - title (h2.show-title anchor text)
  - datetime slug embedded in the anchor href:  YYYY-MM-DDtHHMMSS±HHMM
  - room name (h3 after the time, e.g. "Main Room", "Belly Room")
  - ShowClix ticket URL (showclix.com/event/…)
  - sold_out flag (present when "SOLD OUT" alert appears)
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.core.entities.club.model import Club


# Matches the datetime portion of a Comedy Store URL slug, e.g.
# "2026-03-25t200000-0700" (lowercase t, HHMMSS, ±HHMM offset).
_SLUG_DT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[tT](\d{2})(\d{2})(\d{2})([+-]\d{4})")


def _parse_slug_datetime(slug: str) -> Optional[datetime]:
    """Parse a Comedy Store datetime slug into an aware datetime.

    slug format: "2026-03-25t200000-0700[-title-words]"
    'Z' UTC offsets are normalised to '+0000' before parsing.
    Returned datetime has the UTC offset from the slug applied.
    Returns None if the slug does not match the expected format.
    """
    slug = slug.replace("Z", "+0000")
    m = _SLUG_DT_RE.match(slug)
    if not m:
        return None
    date_part, hh, mm, ss, tz = m.groups()
    # Reconstruct an ISO 8601 string that Python's strptime understands
    iso = f"{date_part}T{hh}{mm}{ss}{tz}"
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H%M%S%z")
    except ValueError:
        return None


@dataclass
class ComedyStoreEvent(ShowConvertible):
    """A single show scraped from thecomedystore.com/calendar."""

    title: str
    datetime_slug: str  # e.g. "2026-03-25t200000-0700"
    ticket_url: str     # ShowClix URL (or show-page URL if sold out / free)
    room: str = ""
    sold_out: bool = False

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show entity."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.datetime_slug:
            return None

        start_date = _parse_slug_datetime(self.datetime_slug)
        if not start_date:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, sold_out=self.sold_out)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            tickets=tickets,
            room=self.room,
            enhanced=enhanced,
        )
