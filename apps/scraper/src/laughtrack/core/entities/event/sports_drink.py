"""
Data model for a single event from Sports Drink (New Orleans).

Show data is scraped from the OpenDate listing page at:
  https://app.opendate.io/v/sports-drink-1939?per_page=500

Each event card (div.confirm-card) provides:
- title via p.mb-0.text-dark > a > strong
- event/ticket URL via p.mb-0.text-dark > a[href]
- date string via the first blue p.mb-0 (e.g. "March 29, 2026")
- time string via the second blue p.mb-0 (e.g. "Doors: 7:30 PM - Show: 8:30 PM")
"""

import pytz
import re

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

def _parse_opendate_datetime(
    date_str: str, time_str: str, timezone_name: str
) -> Optional[datetime]:
    """
    Parse a date like "March 29, 2026" and a time string like
    "Doors: 7:30 PM - Show: 8:30 PM" and localize to *timezone_name*.

    Extracts the show time (after "Show: ") from time_str.  Handles both
    spaced ("8:30 PM") and compact ("8:30PM") AM/PM formats.
    Returns None if parsing fails.
    """
    try:
        date_str = date_str.strip()
        naive_date = datetime.strptime(date_str, "%B %d, %Y")

        # Extract "8:30 PM" (or "8:30PM") from "Doors: 7:30 PM - Show: 8:30 PM"
        match = re.search(r"Show:\s*(\d{1,2}:\d{2}\s*[AP]M)", time_str, re.IGNORECASE)
        if not match:
            return None
        # Normalise compact format ("8:30PM" → "8:30 PM") so strptime succeeds
        show_time_str = re.sub(r"\s*([AP]M)\s*$", r" \1", match.group(1).strip(), flags=re.IGNORECASE)
        naive_time = datetime.strptime(show_time_str, "%I:%M %p")

        naive = naive_date.replace(
            hour=naive_time.hour,
            minute=naive_time.minute,
            second=0,
            microsecond=0,
        )
        tz = pytz.timezone(timezone_name)
        return tz.localize(naive)
    except Exception:
        return None


@dataclass
class SportsDrinkEvent(ShowConvertible):
    """
    A single event scraped from the Sports Drink OpenDate page.
    """

    title: str       # e.g. "Ian Lara at SPORTS DRINK (Friday, 7:00p)"
    date_str: str    # e.g. "April 03, 2026"
    time_str: str    # e.g. "Doors: 6:30 PM - Show: 7:00 PM"
    event_url: str   # e.g. "https://app.opendate.io/e/ian-lara-at-sports-drink-..."

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.time_str or not self.event_url:
            return None

        start_dt = _parse_opendate_datetime(
            self.date_str, self.time_str, club.timezone or "America/Chicago"
        )
        if start_dt is None:
            return None

        ticket_url = url or self.event_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
