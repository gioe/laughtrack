"""
Data model for a single event from Goofs Comedy Club.

Show data is extracted from the Next.js RSC payload embedded in the /p/shows listing page.
"""

import re
from dataclasses import dataclass
from typing import Optional

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.core.entities.club.model import Club


_TIME_RE = re.compile(r'^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$', re.IGNORECASE)


def _normalize_time(time_str: str) -> str:
    """Normalise time strings to 'H:MM AM/PM' format.

    Handles both '9:00 PM' and compact forms like '9PM' / '11PM'.
    """
    m = _TIME_RE.match(time_str.strip())
    if m:
        hour = m.group(1)
        minutes = m.group(2) or "00"
        ampm = m.group(3).upper()
        return f"{hour}:{minutes} {ampm}"
    return time_str


@dataclass
class GoofsEvent(ShowConvertible):
    """
    Data model representing a single show from Goofs Comedy Club.

    Fields map directly to the JSON objects in the `initialShows` array
    embedded in the site's Next.js RSC payload.
    """

    id: int
    slug: str           # "YYYY-MM-DD-HHMM" or numeric string
    date: str           # "YYYY-MM-DD"
    time: str           # normalised "H:MM AM/PM" (e.g. "9:00 PM")
    display_title: str
    headliner_name: Optional[str] = None
    price_ga_cents: Optional[int] = None  # fee-inclusive price in cents

    @property
    def show_page_url(self) -> str:
        return f"https://goofscomedy.com/p/show/{self.slug}"

    @classmethod
    def from_dict(cls, data: dict) -> "GoofsEvent":
        """Create a GoofsEvent from a raw show dict from the RSC payload."""
        return cls(
            id=int(data.get("id", 0)),
            slug=str(data.get("slug", data.get("id", ""))),
            date=data.get("date", ""),
            time=_normalize_time(data.get("time", "")),
            display_title=data.get("computedDisplayTitle") or data.get("title") or "",
            headliner_name=data.get("headlinerName") or None,
            price_ga_cents=data.get("priceGaCents") or None,
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.display_title or not self.date or not self.time:
            return None

        # Combine date + time into a parseable string: "2026-03-27 9:00 PM"
        datetime_str = f"{self.date} {self.time}"
        start_date = ShowFactoryUtils.safe_parse_datetime_string(
            datetime_str, "%Y-%m-%d %I:%M %p", club.timezone or "America/New_York"
        )
        if not start_date:
            return None

        lineup = []
        if self.headliner_name:
            lineup = ShowFactoryUtils.create_lineup_from_performers([self.headliner_name])

        price = (self.price_ga_cents / 100.0) if self.price_ga_cents else 0.0
        ticket_url = url or self.show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.display_title,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=lineup,
            tickets=tickets,
            enhanced=enhanced,
        )
