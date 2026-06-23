"""
Data model for a single TicketSpice (Webconnex) ticketing-form event.

TicketSpice forms (``<account>.ticketspice.com/<form-slug>``) are single-event
ticketing pages: one form == one show on one date, with one or more ticket
levels. The form page embeds its config in a ``window.__BOOTSTRAP__`` JS object —
``appSettings`` carries ``formName`` (the show title), ``eventStart`` (an ISO
date at UTC midnight — date only, NO reliable wall-clock time), ``timeZone``, and
``status``; ``formData`` carries the ticket ``levels`` (price). The extractor
parses those into one :class:`TicketSpiceEvent`.

Because ``eventStart`` carries no show time, ``to_show`` combines the parsed date
with a configurable default show time (``default_show_time`` on the scraping
source, default 19:00) localized to the club timezone — same pattern as the AXS
homepage scraper.
"""

import pytz

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

_DEFAULT_SHOW_TIME = "19:00"


def _parse_default_time(raw: Optional[str]) -> time:
    """Parse an ``HH:MM`` default show time, falling back to 19:00."""
    try:
        hh, mm = (raw or _DEFAULT_SHOW_TIME).split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return time(19, 0)


@dataclass
class TicketSpiceEvent(ShowConvertible):
    """A single show parsed from one TicketSpice ticketing form."""

    title: str                      # appSettings.formName, e.g. "Barley & Me ... Comedy Show"
    event_date: date                # date portion of appSettings.eventStart (no time)
    form_url: str                   # the TicketSpice form URL (drives ticket purchase)
    price: Optional[float] = None   # lowest ticket-level price, if parsed

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are
        missing or the show date is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.event_date or not self.form_url:
            return None

        default_time = _parse_default_time(club.metadata_value("default_show_time"))
        naive = datetime.combine(self.event_date, default_time)
        start_dt = pytz.timezone(club.timezone or "America/Los_Angeles").localize(naive)

        # Single-date TicketSpice forms go stale once the show passes; drop them
        # so an un-updated form doesn't keep emitting a past show every night.
        # Compare on date (not the wall-clock default time) so a same-day show is
        # never dropped just because the configured default time has elapsed.
        if start_dt.date() < datetime.now(timezone.utc).astimezone(start_dt.tzinfo).date():
            return None

        source_url = url or self.form_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(source_url, price=self.price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=source_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
