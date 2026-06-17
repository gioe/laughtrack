"""
Data model for a single event from the Playhouse Square (Cleveland) website.

Playhouse Square runs a custom carbonhouse "showtime" CMS (RequireJS, NOT
WordPress/Tessitura — see SCRAPERS.md). Its public event list is served as
``m-eventItem`` cards by a load-more AJAX feed
(``/events/events_ajax/{offset}?per_page=N``) whose JSON payload is an
HTML-string of those cards. Each card carries a title, a date (single date or a
range — no show time), the producing venue name (``venue_title``), and a ticket
link to the ``tickets.playhousesquare.org`` Tessitura box office.

The list carries the date but **no show time**, so ``to_show`` combines the
parsed date with a configurable default show time (``default_show_time`` on the
scraping source, default 19:00) localized to the club timezone. ``show_page_url``
points at the venue's own ``/events/detail/<slug>`` page (drives traffic to the
venue), while the ticket link points at the box office.
"""

import pytz

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

# List-page date, e.g. "Oct 22, 2026" (abbreviated month) or "June 17, 2026"
# (full month — Playhouse Square renders the current month's name in full and
# other months abbreviated).
_PHS_DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y")
_DEFAULT_SHOW_TIME = "19:00"


def _parse_phs_date(date_str: str):
    """Parse a Playhouse Square list date, tolerating abbreviated and full
    month names. Returns a ``date`` or None if neither format matches."""
    cleaned = " ".join((date_str or "").split())
    for fmt in _PHS_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _parse_default_time(raw: Optional[str]) -> time:
    """Parse an ``HH:MM`` default show time, falling back to 19:00."""
    try:
        hh, mm = (raw or _DEFAULT_SHOW_TIME).split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return time(19, 0)


@dataclass
class PlayhouseSquareEvent(ShowConvertible):
    """A single event scraped from the Playhouse Square event feed."""

    title: str            # e.g. "Marc Maron"
    date_str: str         # e.g. "Oct 22, 2026" (date only — no time)
    show_page_url: str    # the venue's own /events/detail/<slug> page
    venue_title: str = ""  # producing PHS theatre, e.g. "Mimi Ohio Theatre"
    ticket_url: Optional[str] = None  # tickets.playhousesquare.org box-office link

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are
        missing or the show date is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.show_page_url:
            return None

        date_only = _parse_phs_date(self.date_str)
        if date_only is None:
            return None

        default_time = _parse_default_time(club.metadata_value("default_show_time"))
        naive = datetime.combine(date_only, default_time)
        start_dt = pytz.timezone(club.timezone or "America/New_York").localize(naive)

        if start_dt < datetime.now(timezone.utc):
            return None

        show_page_url = url or self.show_page_url
        purchase_url = self.ticket_url or show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(purchase_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
