"""
Data model for a single event from Laffs Comedy Cafe (Tucson, AZ).

Show data is scraped from the venue's coming-soon page at:
  https://www.laffstucson.com/coming-soon.html

Each show is listed in a div.comicBox with:
- h2.comic-listing-name — comedian name
- Radio button labels in the reservation form — individual showtimes
  (e.g. "Friday, April 10 @ 8 PM")

The venue sells tickets directly (no third-party platform), so ticket URLs
point to the coming-soon page itself.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


def _parse_showtime(showtime_str: str, timezone_name: str) -> Optional[datetime]:
    """
    Parse a showtime like "Friday, April 10 @ 8 PM" or
    "Saturday, April 11 @ 10:30 PM" into a timezone-aware datetime.

    Returns None if parsing fails.
    """
    try:
        # Extract "April 10 @ 8 PM" or "April 10 @ 10:30 PM"
        match = re.match(
            r"\w+,\s+(\w+ \d{1,2})\s+@\s+(\d{1,2}(?::\d{2})?\s*[AP]M)",
            showtime_str.strip(),
            re.IGNORECASE,
        )
        if not match:
            return None

        date_part = match.group(1)  # "April 10"
        time_part = match.group(2).strip()  # "8 PM" or "10:30 PM"

        # Normalize time: "8 PM" → "8:00 PM", "10:30 PM" stays
        if ":" not in time_part:
            time_part = re.sub(
                r"(\d+)\s*([AP]M)", r"\1:00 \2", time_part, flags=re.IGNORECASE
            )

        # Add current year, bumping to next year if the month is in the past
        now = datetime.now()
        full_str = f"{date_part}, {now.year} {time_part}"
        naive = datetime.strptime(full_str, "%B %d, %Y %I:%M %p")

        if naive.month < now.month:
            naive = naive.replace(year=now.year + 1)

        tz = pytz.timezone(timezone_name)
        return tz.localize(naive)
    except Exception:
        return None


@dataclass
class LaffsComedyCafeEvent(ShowConvertible):
    """A single showtime from Laffs Comedy Cafe."""

    comedian_name: str  # e.g. "Adam Dominguez"
    showtime_str: str  # e.g. "Friday, April 10 @ 8 PM"
    ticket_url: str  # e.g. "https://www.laffstucson.com/coming-soon.html"
    # Priced seating tiers recovered from the purchase flow's seating selector,
    # e.g. [("General Admission", 15.0), ("Preferred Seating", 20.0)]. Empty when
    # the page exposes no seating tiers, in which case a single unpriced fallback
    # ticket is emitted.
    seating_tiers: List[Tuple[str, Optional[float]]] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.comedian_name or not self.showtime_str:
            return None

        start_dt = _parse_showtime(
            self.showtime_str, club.timezone or "America/Phoenix"
        )
        if start_dt is None:
            return None

        ticket_url = url or self.ticket_url
        if self.seating_tiers:
            tickets = [
                ShowFactoryUtils.create_fallback_ticket(
                    ticket_url, price=price, ticket_type=ticket_type
                )
                for ticket_type, price in self.seating_tiers
            ]
        else:
            tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.comedian_name,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
