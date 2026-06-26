"""Data model for a single showing scraped from the Dojour event API.

Dojour (https://dojour.us) is a hosted event/ticketing platform that venues
embed on their own sites via an AngularJS calendar iframe
(``https://dojour.us/embed/u/<username>``). It is reusable across any venue on
the platform — the per-venue ``username`` is the only thing that varies, and
the public JSON feed lives at::

    GET https://dojour.us/api/event_instances/user_feed/
        ?username=<username>&date_min=<now>&distinct_event=true&exclude_plans=true

Each feed ``results[]`` row is an *event* whose ``upcoming_showing_set`` lists
every upcoming showtime (a two-night run with a 7pm + 9pm seating yields four
showings). We model one ``DojourEvent`` per *showing* so each showtime persists
as its own Show, mirroring how comedy clubs program distinct seatings.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

DOJOUR_BASE_URL = "https://dojour.us"


def _clean_description(raw: Optional[str]) -> Optional[str]:
    """Strip Dojour's HTML description down to plain text."""
    if not raw:
        return None
    text = BeautifulSoup(str(raw), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


@dataclass
class DojourEvent(ShowConvertible):
    """A single Dojour showing (one event seating) convertible to a Show."""

    event_id: str  # Dojour numeric event id (as string)
    title: str  # Event title, e.g. "Fumi Abe /// Comedy"
    start_dt: str  # Showing start, ISO 8601 with offset
    absolute_url: str  # Dojour event page (the venue's listing)
    showings_url: Optional[str] = None  # call_to_action_url (buy/showings page)
    description: Optional[str] = None
    min_price_cents: Optional[int] = None  # Lowest offer option price, in cents
    timezone_name: str = "America/Chicago"

    @property
    def show_page_url(self) -> str:
        """Absolute Dojour event page URL (the venue's listing source)."""
        if self.absolute_url.startswith("http"):
            return self.absolute_url
        if self.absolute_url:
            return f"{DOJOUR_BASE_URL}{self.absolute_url}"
        return self.showings_url or DOJOUR_BASE_URL

    def _resolve_date(self) -> Optional[datetime]:
        """Parse the showing start into a timezone-aware datetime.

        Dojour emits offsets without a colon (``-0500``), which
        ``parse_datetime_with_timezone`` handles via ``fromisoformat``; on the
        rare chance a start lacks an offset, it is localized to the showing's
        timezone so ``Show.date`` is never naive.
        """
        if not self.start_dt:
            return None
        try:
            return DateTimeUtils.parse_datetime_with_timezone(self.start_dt, self.timezone_name)
        except (ValueError, TypeError):
            return None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this Dojour showing to a Show domain object."""
        start_date = self._resolve_date()
        if start_date is None:
            return None

        page_url = url or self.show_page_url
        ticket_url = self.showings_url or page_url
        price = (self.min_price_cents / 100.0) if self.min_price_cents is not None else None
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            description=_clean_description(self.description),
            supplied_tags=["event"],
            enhanced=enhanced,
        )
