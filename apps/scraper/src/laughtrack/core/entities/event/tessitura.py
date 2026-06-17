"""
Data model for a single Tessitura production showtime (WordPress integration).

Many Tessitura venue operators surface their productions through a WordPress
plugin that exposes ``tessi_production`` / ``tessi_performance`` custom post
types over the standard WP REST API (``/wp-json/wp/v2/tessi_production``) and a
``genre`` taxonomy. Each comedy production carries its title in
``title.rendered`` and its primary showtime + venue + ticket link inside
``content.rendered``, e.g. "Saturday, December 5, 2026 | 7 PM",
"Davidson Theatre, Riffe Center", and a ``https://tickets.{org}.com/{prod}/{perf}/``
purchase URL.

One ``TessituraEvent`` is produced per scraped production (its primary
showtime). The ticketing box office itself (``tickets.{org}.com``) is bot- and
queue-protected, so the WordPress REST feed is the scrapable seam.
"""

import pytz

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

# Tessitura/WordPress showtime format, e.g. "Saturday, December 5, 2026 | 7 PM"
# or "Wednesday, November 25, 2026 | 7:30 PM". The minute portion is optional.
_TESSITURA_DT_FORMATS = (
    "%A, %B %d, %Y | %I:%M %p",
    "%A, %B %d, %Y | %I %p",
)


def _parse_tessitura_datetime(start_date_str: str, timezone_name: str) -> Optional[datetime]:
    """Parse "Saturday, December 5, 2026 | 7 PM" and localize to *timezone_name*.

    Accepts both the minute-bearing ("7:30 PM") and bare-hour ("7 PM") forms.
    Returns None if parsing fails.
    """
    cleaned = " ".join(start_date_str.split())  # collapse whitespace
    for fmt in _TESSITURA_DT_FORMATS:
        try:
            naive = datetime.strptime(cleaned, fmt)
            return pytz.timezone(timezone_name).localize(naive)
        except ValueError:
            continue
    return None


@dataclass
class TessituraEvent(ShowConvertible):
    """A single comedy production showtime from a Tessitura WordPress feed."""

    title: str            # e.g. "Gary Gulman: Misfit Stand Up Tour"
    start_date_str: str   # e.g. "Saturday, December 5, 2026 | 7 PM"
    show_page_url: str    # the WordPress production page (drives traffic to venue)
    ticket_url: Optional[str] = None  # tickets.{org}.com purchase URL, when present
    venue_name: Optional[str] = None  # specific room/theatre, e.g. "Lincoln Theatre"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are missing
        or the showtime is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_date_str or not self.show_page_url:
            return None

        start_dt = _parse_tessitura_datetime(
            self.start_date_str, club.timezone or "America/New_York"
        )
        if start_dt is None:
            return None

        # The comedy feed includes already-passed productions; skip them so we
        # don't persist stale shows.
        if start_dt < datetime.now(timezone.utc):
            return None

        show_page_url = url or self.show_page_url
        # Prefer the box-office purchase URL for the ticket link when present,
        # falling back to the production page so the show is always ticketable.
        purchase_url = self.ticket_url or show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(purchase_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            room=self.venue_name or "",
            enhanced=enhanced,
        )
