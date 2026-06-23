"""Data model for a single event from an AEG/Goldenvoice Carbonhouse venue page.

Many AEG Presents / Goldenvoice venues (The Warfield, The Regency Ballroom,
Social Hall SF, …) run the stock Carbonhouse venue-site template
(``generatorAgent rdf:resource="http://carbonhouse.com/"``) and ticket every
show via AXS (``axs.com/events/<id>/...?skin=<venue>``). The venue's own
``/events`` page is plain server-rendered HTML listing each upcoming show as a
``div.entry`` card carrying:

  - the show name in ``<h3 class="carousel_item_title_small"><a>NAME</a></h3>``
  - the date in ``<span class="date">Wed, Jun 24, 2026</span>``
  - the show time in ``<span class="time">Show 8:00 PM</span>``
  - the venue's own ``/events/detail/<id>`` URL
  - an AXS ticket link ``axs.com/events/<id>/...?skin=<venue>``

The ``axs.com`` detail pages are DataDome-protected, but the venue ``/events``
page is the scrapable seam — handled without ever touching ``axs.com``.

Unlike the generic AXS homepage event
(:mod:`laughtrack.core.entities.event.axs`) and the Pabst venue-page event
(:mod:`laughtrack.core.entities.event.pabst_axs`), the Carbonhouse ``/events``
card carries a **real show time**, so ``to_show`` parses date + time directly
and only falls back to a configurable default time when the card has no parseable
time text.
"""

import pytz

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

_DEFAULT_SHOW_TIME = "19:00"

# Date like "Wed, Jun 24, 2026" -> "%a, %b %d, %Y".
_DATE_FORMAT = "%a, %b %d, %Y"


def _parse_card_date(date_str: str):
    """Parse a ``Wed, Jun 24, 2026`` date string, returning a ``date`` or None."""
    try:
        return datetime.strptime((date_str or "").strip(), _DATE_FORMAT).date()
    except (ValueError, AttributeError):
        return None


def _parse_card_time(time_str: Optional[str]) -> Optional[time]:
    """Parse a ``8:00 PM`` (12-hour) show time, returning a ``time`` or None."""
    raw = (time_str or "").strip()
    if not raw:
        return None
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(raw.upper(), fmt).time()
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
class AEGAXSEvent(ShowConvertible):
    """A single event scraped from an AEG/Goldenvoice Carbonhouse venue page."""

    title: str            # e.g. "The Kevin Langue Show: Live!"
    date_str: str         # "Wed, Jun 24, 2026" from the card's span.date
    show_page_url: str    # the venue's own /events/detail/<id> page
    time_str: Optional[str] = None    # "8:00 PM" from span.time, when present
    ticket_url: Optional[str] = None  # the axs.com ticket URL

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are
        missing or the show date is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.show_page_url:
            return None

        date_only = _parse_card_date(self.date_str)
        if date_only is None:
            return None

        show_time = _parse_card_time(self.time_str)
        if show_time is None:
            show_time = _parse_default_time(club.metadata_value("default_show_time"))

        naive = datetime.combine(date_only, show_time)
        start_dt = pytz.timezone(club.timezone or "America/Los_Angeles").localize(naive)

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
