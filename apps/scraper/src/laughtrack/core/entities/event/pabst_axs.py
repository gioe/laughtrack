"""Data model for a single event from a Pabst Theater Group venue page.

The Pabst Theater Group (pabsttheater.org) runs one shared venue-page template
across its rooms (Pabst Theater, Riverside Theater, Turner Hall, …). Each venue
page is plain server-rendered HTML listing every upcoming show as a
``div.eventItem`` card carrying the show name (in the ticket/info link ``title``
attribute), an AXS ticket link (``axs.com/events/<id>/...?skin=pabst``), the
venue's own detail URL, and a dated thumbnail image
(``assets/img/YYYY.MM.DD-R-<slug>...png``). The ``axs.com`` detail pages are
DataDome-protected, but the venue page is the scrapable seam — handled without
ever touching ``axs.com``.

The thumbnail filename carries the date (``YYYY.MM.DD``) but **no show time**, so
``to_show`` combines the parsed date with a configurable default show time
(``default_show_time`` on the scraping source, default 19:00) localized to the
club timezone. This mirrors the generic AXS venue-homepage event
(:mod:`laughtrack.core.entities.event.axs`); they differ only in date source
(thumbnail filename here vs. an ``<h4>`` text node there).
"""

import pytz

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

_DEFAULT_SHOW_TIME = "19:00"


def _parse_iso_date(date_str: str):
    """Parse a ``YYYY-MM-DD`` date string, returning a ``date`` or None."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _parse_default_time(raw: Optional[str]) -> time:
    """Parse an ``HH:MM`` default show time, falling back to 19:00."""
    try:
        hh, mm = (raw or _DEFAULT_SHOW_TIME).split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return time(19, 0)


@dataclass
class PabstAXSEvent(ShowConvertible):
    """A single event scraped from a Pabst Theater Group venue page."""

    title: str            # e.g. "Ben Schwartz & Friends"
    date_str: str         # ISO "YYYY-MM-DD" parsed from the thumbnail filename
    show_page_url: str    # the venue's own detail page (drives traffic to venue)
    ticket_url: Optional[str] = None  # the axs.com ticket URL
    venue_name: Optional[str] = None
    venue_url: Optional[str] = None

    def venue_payload(self) -> dict:
        """Return a discovery payload for aggregate Pabst event-list routing."""
        name = (self.venue_name or "").strip()
        if not name:
            return {}

        known = _KNOWN_VENUES.get(name.lower(), {})
        return {
            "name": name,
            "address": known.get("address", ""),
            "zip_code": known.get("zip_code", ""),
            "timezone": "America/Chicago",
            "website": self.venue_url or known.get("website", ""),
            "club_type": "venue",
        }

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are
        missing or the show date is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.show_page_url:
            return None

        date_only = _parse_iso_date(self.date_str)
        if date_only is None:
            return None

        default_time = _parse_default_time(club.metadata_value("default_show_time"))
        naive = datetime.combine(date_only, default_time)
        start_dt = pytz.timezone(club.timezone or "America/Chicago").localize(naive)

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


_KNOWN_VENUES = {
    "the pabst theater": {
        "address": "144 E Wells St, Milwaukee, WI",
        "zip_code": "53202",
        "website": "https://www.pabsttheatergroup.com/venues/detail/the-pabst-theater",
    },
    "the riverside theater": {
        "address": "116 W Wisconsin Ave, Milwaukee, WI",
        "zip_code": "53203",
        "website": "https://www.pabsttheatergroup.com/venues/detail/the-riverside-theater",
    },
    "turner hall ballroom": {
        "address": "1040 Vel R. Phillips Avenue, Milwaukee, WI",
        "zip_code": "53203",
        "website": "https://www.pabsttheatergroup.com/venues/detail/turner-hall-ballroom",
    },
    "miller high life theatre": {
        "address": "500 West Kilbourn Avenue, Milwaukee, WI",
        "zip_code": "53203",
        "website": "https://www.pabsttheatergroup.com/venues/detail/miller-high-life-theatre",
    },
    "vivarium": {
        "address": "1818 North Farwell Avenue, Milwaukee, WI",
        "zip_code": "53202",
        "website": "https://www.pabsttheatergroup.com/venues/detail/vivarium",
    },
    "the fitzgerald": {
        "address": "1119 North Marshall Street, Milwaukee, WI",
        "zip_code": "53202",
        "website": "https://www.pabsttheatergroup.com/venues/detail/the-fitzgerald-venue",
    },
    "fiserv forum": {
        "address": "1111 Vel R. Phillips Avenue, Milwaukee, WI",
        "zip_code": "53203",
        "website": "https://www.fiservforum.com",
    },
    "mo's irish pub": {
        "address": "142 W Wisconsin Ave, Milwaukee, WI",
        "zip_code": "53203",
        "website": "https://www.mosirishpub.com",
    },
}
