"""Parser for Ticket Tailor box-office listing HTML (tickettailor.com).

The listing at ``tickettailor.com/events/<account>/`` is server-rendered HTML
(no reliable JSON-LD). Each event is an ``li.events-listing__item`` card:

- ``h3.event__title`` / ``a.event__link`` — title + detail link /events/<acct>/{id}
- ``span.event-meta__date``     — "Tue Jun 30, 2026 6:00 PM - 9:00 PM CDT"
- ``span.event-meta__location`` — "Vendetta Coffee Bar, 53204" (name + zip)

The account is a roving producer, so each event carries its OWN venue. The date
string carries the year and a US timezone abbreviation, which we map to an IANA
zone for localization.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.ticket_tailor import TicketTailorEvent

_TT_BASE = "https://www.tickettailor.com"

# "Tue Jun 30, 2026 6:00 PM - 9:00 PM CDT" (spaces re-inserted by get_text(' ')).
#   weekday  month   day      year       start time
_DATE_RE = re.compile(
    r"\b(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s*,?\s*(?P<year>\d{4})\s+"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>[AP]M)",
    re.IGNORECASE,
)

# US timezone abbreviation — matched case-sensitively and separately from the
# date so an IGNORECASE date match can't swallow a prose word as the tz.
_TZ_RE = re.compile(r"\b([CEMP][SD]T)\b")

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# US timezone abbreviation -> IANA zone. Daylight/standard both map to the same
# IANA zone (the offset is resolved by the date). Covers the contiguous US
# zones indie comedy venues use; unknown abbreviations fall back to the venue
# club's own timezone downstream.
_TZ_ABBR = {
    "EST": "America/New_York", "EDT": "America/New_York",
    "CST": "America/Chicago", "CDT": "America/Chicago",
    "MST": "America/Denver", "MDT": "America/Denver",
    "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
}

_ZIP_RE = re.compile(r"\b(\d{5})\b")


def listing_url_for_account(account_slug: str) -> str:
    """Build the canonical Ticket Tailor box-office URL for an account slug."""
    return f"{_TT_BASE}/events/{account_slug}/"


def extract_account_slug(url: str) -> Optional[str]:
    """Return the account slug from a Ticket Tailor box-office URL, or None."""
    if not url:
        return None
    match = re.search(r"tickettailor\.com/(?:events|all-tickets)/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def extract_events(html: str) -> List[TicketTailorEvent]:
    """Parse a Ticket Tailor listing page into TicketTailorEvent objects."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    events: List[TicketTailorEvent] = []

    for card in soup.select("li.events-listing__item"):
        link = card.find("a", class_="event__link") or card.find(
            "a", href=re.compile(r"/events/[^/]+/\d+")
        )
        if link is None:
            continue
        event_url = urljoin(_TT_BASE, link.get("href", ""))

        title_el = card.find(class_="event__title") or link
        title = title_el.get_text(strip=True)

        date_el = card.find("span", class_="event-meta__date")
        if date_el is None:
            continue
        parsed = _parse_datetime(date_el.get_text(" ", strip=True))
        if parsed is None:
            continue
        start, tz = parsed

        loc_el = card.find("span", class_="event-meta__location")
        venue_name, venue_zip = _parse_location(
            loc_el.get_text(" ", strip=True) if loc_el else ""
        )

        events.append(
            TicketTailorEvent(
                title=title,
                start=start,
                event_url=event_url,
                venue_name=venue_name,
                venue_zip=venue_zip,
                timezone=tz,
            )
        )

    return events


def _parse_datetime(text: str) -> Optional[Tuple[datetime, Optional[str]]]:
    """Parse the event-meta date string into (naive datetime, IANA tz | None)."""
    match = _DATE_RE.search(text or "")
    if not match:
        return None
    month = _MONTHS.get(match.group("mon").lower())
    if month is None:
        return None

    day = int(match.group("day"))
    year = int(match.group("year"))
    hour = int(match.group("hour")) % 12
    if match.group("ampm").upper() == "PM":
        hour += 12
    minute = int(match.group("minute"))

    tz_match = _TZ_RE.search(text or "")
    tz = _TZ_ABBR.get(tz_match.group(1)) if tz_match else None

    try:
        return datetime(year, month, day, hour, minute), tz
    except ValueError:
        return None


def _parse_location(text: str) -> Tuple[str, str]:
    """Split 'Venue Name, 53204' into (venue_name, zip). Zip optional."""
    text = (text or "").strip()
    if not text:
        return "", ""
    zip_match = _ZIP_RE.search(text)
    venue_zip = zip_match.group(1) if zip_match else ""
    # Venue name is everything before the trailing ", <zip>" (or the whole
    # string when no zip is present).
    name = text
    if venue_zip:
        name = re.sub(r",?\s*" + re.escape(venue_zip) + r"\s*$", "", text).strip()
    return name.rstrip(", ").strip(), venue_zip
