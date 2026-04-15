"""
Data model for a single event from The Bit Theater (Aurora, IL).

Show data is scraped from the Odoo-based website at:
  https://www.bitimprov.org/event

Pipeline:
  Listing page → article cards (with category filter) →
  optional detail page fetch (price) → BitTheaterEvent → Show
"""

import re

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


# Categories that indicate comedy-relevant events.
_COMEDY_CATEGORIES = frozenset(
    [
        "stand-up",
        "short form",
        "long form",
        "improv",
        "sketch",
        "comedy",
        "stand up",
        "open mic",
        "standup",
    ]
)

# Categories that should always be excluded, even if mixed with comedy tags.
_EXCLUDE_CATEGORIES = frozenset(
    [
        "class",
        "play",
        "burlesque",
        "drag",
        "role playing",
        "musical",
        "dance",
        "workshop",
        "camp",
        "audition",
    ]
)


def is_comedy_relevant(categories: List[str]) -> bool:
    """Return True if the event's category tags indicate a comedy show."""
    if not categories:
        return False

    lower_cats = [c.lower().strip() for c in categories]

    # Exclude if any exclusion category is present
    for cat in lower_cats:
        if cat in _EXCLUDE_CATEGORIES:
            return False

    # Include if any comedy category matches
    for cat in lower_cats:
        if cat in _COMEDY_CATEGORIES:
            return True

    return False


def _parse_odoo_utc(dt_str: str, timezone_name: str) -> Optional[datetime]:
    """
    Parse a UTC datetime string from Odoo's itemprop startDate and localize it.

    Odoo emits dates as "2026-04-17T01:00:00" (no Z suffix) or
    "2026-04-17 01:00:00Z" — both are UTC.
    """
    if not dt_str:
        return None
    try:
        # Normalize: strip Z suffix and replace space with T
        cleaned = dt_str.strip().rstrip("Z").replace(" ", "T")
        naive = datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S")
        utc = pytz.utc.localize(naive)
        tz = pytz.timezone(timezone_name)
        return utc.astimezone(tz)
    except Exception:
        return None


@dataclass
class BitTheaterEvent(ShowConvertible):
    """
    A single event scraped from The Bit Theater's Odoo events page.
    """

    title: str
    start_datetime_utc: str  # e.g. "2026-04-17T01:00:00"
    event_url: str  # e.g. "https://www.bitimprov.org/event/thursday-triple-threat-459/"
    categories: List[str] = field(default_factory=list)
    price: Optional[float] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_datetime_utc or not self.event_url:
            return None

        tz_name = club.timezone or "America/Chicago"
        start_dt = _parse_odoo_utc(self.start_datetime_utc, tz_name)
        if start_dt is None:
            return None

        ticket_url = url or self.event_url
        price = self.price if self.price and self.price > 0 else 0.0
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            tickets=tickets,
            enhanced=enhanced,
        )
