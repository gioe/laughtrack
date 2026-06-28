"""Data model for a single show occurrence from a WellAttended venue.

WellAttended (``<venue>.wellattended.com``) is a Next.js RSC ticketing platform.
Each ``/events/<slug>`` detail page embeds its showing/occurrence objects in the
``self.__next_f.push(...)`` RSC flight stream (no JSON-LD, no ``__NEXT_DATA__``):

    {"_id", "thingId", "thingTitle", "start": "$D<UTC ISO>", "timezone",
     "soldCount", "remainingCapacity", "shouldBeShown", "deleted", "slug", ...}

plus ticket-tier objects carrying ``price`` (in **cents**). One
``WellAttendedEvent`` is built per upcoming occurrence; ``show_page_url`` /
ticket point at the venue's own ``/events/<slug>`` page.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


def _parse_wellattended_utc(start_time_utc: str, timezone_name: str) -> Optional[datetime]:
    """Parse a UTC ISO timestamp (``2026-08-08T01:30:00.000Z``) into the club tz."""
    try:
        naive = datetime.strptime(start_time_utc, "%Y-%m-%dT%H:%M:%S.%fZ")
        utc = pytz.utc.localize(naive)
        return utc.astimezone(pytz.timezone(timezone_name))
    except Exception:
        return None


@dataclass
class WellAttendedEvent(ShowConvertible):
    """A single upcoming show occurrence from a WellAttended ``/events/<slug>`` page.

    ``start_time_utc`` is the occurrence ``start`` with the RSC ``$D`` marker
    already stripped (a plain UTC ISO string). ``price`` is the cheapest ticket
    tier in **dollars** (``None`` when no tier price is present).
    """

    title: str
    start_time_utc: str
    timezone: str
    show_page_url: str
    price: Optional[float] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert to a Show domain object."""
        if not self.title or not self.start_time_utc:
            return None

        tz_name = self.timezone or club.timezone or "America/Denver"
        start_dt = _parse_wellattended_utc(self.start_time_utc, tz_name)
        if start_dt is None:
            return None

        page_url = url or self.show_page_url
        tickets = []
        if page_url:
            tickets.append(
                ShowFactoryUtils.create_fallback_ticket(page_url, price=self.price)
            )

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
