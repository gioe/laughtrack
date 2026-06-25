"""
Data model for a single event from a Multipass venue box-office page.

Multipass (multipass.com) is a server-rendered event-ticketing platform. Each
venue gets its own subdomain (e.g. ``denvercomedy.multipass.com``) whose root
page lists every upcoming show as a ``div.eventCard2026`` card. All show data
(title, date/time, price, ticket URL) is present in the static HTML — no
detail-page fetch is required.

Each card provides:
- title via ``div.title > a``
- a relative show/ticket path via the card ``a`` hrefs (e.g. ``/maceyisaacs``)
- a human date/time string via ``div.eventline.datetime`` (e.g. "Fri Jul 3 • 8 PM");
  the year is NOT printed and is inferred from the weekday + month/day.
- price via ``span.eventPrice`` (e.g. "$18.06")
"""

import pytz

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

import re

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "Fri Jul 3 • 8 PM"  /  "Sat Jul 25 • 7:30 PM"
_DATETIME_RE = re.compile(
    r"(?P<wd>[A-Za-z]{3,9})\s+"
    r"(?P<mon>[A-Za-z]{3,9})\s+"
    r"(?P<day>\d{1,2})\b.*?"
    r"(?P<hour>\d{1,2})(?::(?P<min>\d{2}))?\s*"
    r"(?P<ampm>[AaPp][Mm])",
    re.DOTALL,
)


def _infer_year(month: int, day: int, weekday_abbr: Optional[str], now: datetime) -> int:
    """
    Multipass cards omit the year. Infer it from the weekday + month/day, picking
    the nearest occurrence on or after today. When a weekday is given it uniquely
    disambiguates the year within a multi-year window; otherwise fall back to the
    current/next year by date alone. Handles the Dec -> Jan rollover.
    """
    candidates = []
    for y in range(now.year - 1, now.year + 3):
        try:
            d = date(y, month, day)
        except ValueError:
            continue
        if weekday_abbr and d.strftime("%a").lower() != weekday_abbr[:3].lower():
            continue
        candidates.append(d)

    future = [d for d in candidates if d >= now.date() - timedelta(days=2)]
    if future:
        return min(future).year
    if candidates:
        return max(candidates).year
    return now.year


def parse_multipass_datetime(text: str, now: Optional[datetime] = None) -> Optional[str]:
    """
    Parse a Multipass card date/time string (e.g. "Fri Jul 3 • 8 PM") into a naive
    ISO string ("YYYY-MM-DDTHH:MM"), inferring the (unprinted) year. Returns None
    when the string cannot be parsed.
    """
    if not text:
        return None
    now = now or datetime.now()
    m = _DATETIME_RE.search(text)
    if not m:
        return None

    month = _MONTHS.get(m.group("mon")[:3].lower())
    if not month:
        return None
    day = int(m.group("day"))

    hour = int(m.group("hour"))
    minute = int(m.group("min")) if m.group("min") else 0
    ampm = m.group("ampm").lower()
    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    year = _infer_year(month, day, m.group("wd"), now)
    try:
        return datetime(year, month, day, hour, minute).strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return None


@dataclass
class MultipassEvent(ShowConvertible):
    """A single upcoming show scraped from a Multipass venue box-office page."""

    title: str              # e.g. "Dude, IDK presents MACEY ISAACS Looks Alive Tour"
    start_iso: str          # naive "YYYY-MM-DDTHH:MM" with inferred year
    show_url: str           # absolute Multipass event page / ticket URL
    price: Optional[float] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_iso or not self.show_url:
            return None

        try:
            naive = datetime.strptime(self.start_iso, "%Y-%m-%dT%H:%M")
            tz = pytz.timezone(club.timezone or "America/Denver")
            start_dt = tz.localize(naive)
        except Exception:
            return None

        ticket_url = url or self.show_url
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(ticket_url, price=self.price)
        ]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=self.show_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
