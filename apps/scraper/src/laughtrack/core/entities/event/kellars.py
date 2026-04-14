"""
Data model for a single event from Kellar's: Modern Magic and Comedy Club.

Events are scraped from the /tc-events/ listing page, which is a WordPress
site using the Starter Events Calendar plugin.  Each event card provides
a performer name, subtitle (role), a single date, time string, price,
and a URL to the individual event page.

Multi-day date ranges (e.g. "April 17 & 18, 2026") are expanded at
extraction time — one KellarsEvent per date — so each event maps 1:1
to a Show.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

# Parse "7:00 P.M." or "6:00 p.m." — standard H:MM AM/PM
_TIME_RE = re.compile(r"(\d{1,2}:\d{2})\s*(P\.?M\.?|A\.?M\.?)", re.IGNORECASE)

# Extract the first time from strings like "Showtime: 1:00 p.m."
_SHOWTIME_RE = re.compile(r"Showtime:\s*(\d{1,2}:\d{2})\s*(P\.?M\.?|A\.?M\.?)", re.IGNORECASE)


def _normalize_ampm(raw: str) -> str:
    """Normalize 'P.M.' / 'p.m.' / 'PM' → 'PM'."""
    return raw.upper().replace(".", "")


def _extract_first_time(time_str: str) -> Optional[str]:
    """
    Pull the earliest show time from a time string.

    Handles:
      - "7:00 P.M."
      - "Brunch begins at 11:00 a.m. | Showtime: 1:00 p.m."
      - "All Shows: 7:00 P.M."
      - "Friday: 7:00 P.M.  Saturday 6:00 P.M. & 8:30 P.M."

    Returns normalized "H:MM PM" string, or None.
    """
    # Prefer explicit "Showtime:" marker
    m = _SHOWTIME_RE.search(time_str)
    if m:
        return f"{m.group(1)} {_normalize_ampm(m.group(2))}"

    # Otherwise take the first time found
    m = _TIME_RE.search(time_str)
    if m:
        return f"{m.group(1)} {_normalize_ampm(m.group(2))}"

    return None


def parse_date_range(date_str: str) -> List[date]:
    """
    Parse Kellar's date strings into a list of dates.

    Formats handled:
      - "May 3, 2026"                → [May 3]
      - "April 17 & 18, 2026"        → [April 17, April 18]
      - "May 28 - 30, 2026"          → [May 28, May 29, May 30]
      - "October 1-3, 2026"          → [Oct 1, Oct 2, Oct 3]
      - "July 29 - 31"              → [Jul 29, Jul 30, Jul 31] (infer year)
      - "September 18 & 19"          → [Sep 18, Sep 19] (infer year)
    """
    s = date_str.strip()

    # Extract year if present (e.g. ", 2026")
    year_match = re.search(r",\s*(\d{4})\s*$", s)
    if year_match:
        year = int(year_match.group(1))
        s = s[: year_match.start()].strip()
    else:
        year = date.today().year

    # Extract month name and day portion
    month_match = re.match(r"([A-Za-z]+)\s+(.+)", s)
    if not month_match:
        return []

    month_name = month_match.group(1)
    rest = month_match.group(2).strip()

    # Parse the day(s) — could be "17 & 18", "28 - 30", "1-3", or just "3"
    if "&" in rest:
        day_parts = [d.strip() for d in rest.split("&")]
    elif " - " in rest:
        day_parts = [d.strip() for d in rest.split(" - ")]
    elif "-" in rest:
        day_parts = [d.strip() for d in rest.split("-")]
    else:
        day_parts = [rest.strip()]

    dates: List[date] = []

    if len(day_parts) == 2:
        try:
            start_day = int(day_parts[0])
            end_day = int(day_parts[1])
        except ValueError:
            return []

        if "&" in date_str:
            # "&" means only the two listed days (not a continuous range)
            for day in [start_day, end_day]:
                try:
                    d = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y").date()
                    dates.append(d)
                except ValueError:
                    pass
        else:
            # Range — include all days from start to end
            for day in range(start_day, end_day + 1):
                try:
                    d = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y").date()
                    dates.append(d)
                except ValueError:
                    pass
    else:
        try:
            d = datetime.strptime(f"{month_name} {day_parts[0]} {year}", "%B %d %Y").date()
            dates.append(d)
        except ValueError:
            pass

    # If no year was given and all dates are in the past, bump to next year
    if not year_match and dates:
        today = date.today()
        if all(d < today - timedelta(days=1) for d in dates):
            dates = [d.replace(year=d.year + 1) for d in dates]

    return dates


def _parse_price(price_str: str) -> Optional[float]:
    """Extract numeric price from '$25' or '$30'."""
    m = re.search(r"\$(\d+(?:\.\d{2})?)", price_str)
    return float(m.group(1)) if m else None


@dataclass
class KellarsEvent(ShowConvertible):
    """
    A single show date from Kellar's event listing page.

    Multi-day listings are expanded at extraction time so each
    KellarsEvent represents exactly one date/show.
    """

    title: str        # e.g. "Ivan Pecel"
    subtitle: str     # e.g. "Comedy Juggler"
    event_date: date  # single date for this show
    time_str: str     # e.g. "7:00 P.M."
    price_str: str    # e.g. "$25"
    event_url: str    # e.g. "https://kellarsmagic.com/tc-events/53593/"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a single Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.event_url:
            return None

        show_time = _extract_first_time(self.time_str)
        if not show_time:
            return None

        datetime_str = (
            f"{self.event_date.year}-{self.event_date.month:02d}"
            f"-{self.event_date.day:02d} {show_time}"
        )
        start_dt = ShowFactoryUtils.safe_parse_datetime_string(
            datetime_str, "%Y-%m-%d %I:%M %p", club.timezone or "America/New_York"
        )
        if start_dt is None:
            return None

        show_page_url = url or self.event_url
        ticket = ShowFactoryUtils.create_fallback_ticket(show_page_url)
        price = _parse_price(self.price_str)
        if price is not None:
            ticket.price = price

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=[ticket],
            enhanced=enhanced,
        )
