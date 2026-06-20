"""Parsers for Tempo Tickets (tempotickets.com) server-rendered PHP HTML.

Two page types, both plain server-rendered HTML (browser UA, no JSON-LD / API /
auth / anti-bot):

1. **Listing** ``listing.php?c=<id>`` — one ``div.listing_table_row`` per
   recurring event, each containing ``<a href='.../event/{code}'>{title}</a>``.
   :func:`extract_event_links` returns ``(code, title, url)`` tuples.

2. **Event** ``/event/{code}`` — upcoming individual dates live in
   ``<select name='EventDateID'><option value='{dateId}'>Fri Jun 26 @ 7:30pm
   (...)</option>...</select>``. Past dates render as ``div.date_past`` and are
   NOT in the select, so we never have to filter them out here. The first
   option (``value='0'``) is a placeholder with empty text and is skipped.
   :func:`extract_event_dates` returns one parsed ``(date_id, datetime)`` per
   upcoming option.

Year inference (GOTCHA): option text carries no year ('Fri Jun 26 @ 7:30pm').
Since the select only lists upcoming dates, we resolve the year by rolling over
from a reference date: the first candidate year that lands the month/day on or
after (reference − slack) wins, so a December scrape correctly reads a 'Jan 9'
option as next year.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

_TEMPO_BASE = "https://www.tempotickets.com"

# 'Fri Jun 26 @ 7:30pm (Doors, Bar & Restaurant open 6pm)'
#  ^weekday ^mon ^day   ^time   ^ampm
_OPTION_RE = re.compile(
    r"\b(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s*@\s*"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>[ap]m)\b",
    re.IGNORECASE,
)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# A date this many days before the reference date is treated as belonging to
# next year (handles the Dec -> Jan rollover without misreading a date that is
# only a few days stale on a boundary scrape).
_ROLLOVER_SLACK_DAYS = 90


def listing_url_for_category(category_id: str) -> str:
    """Build the canonical Tempo listing URL for a venue/category key."""
    return f"{_TEMPO_BASE}/tempotickets/site/pages/listing.php?c={category_id}"


def extract_event_links(html: str) -> List[Tuple[str, str, str]]:
    """Return ``(event_code, title, absolute_url)`` for each listed event.

    Order-preserving and deduplicated by event code.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    results: List[Tuple[str, str, str]] = []

    for anchor in soup.find_all("a", href=re.compile(r"/event/[A-Za-z0-9]+")):
        href = anchor.get("href", "")
        match = re.search(r"/event/([A-Za-z0-9]+)", href)
        if not match:
            continue
        code = match.group(1)
        if code in seen:
            continue
        seen.add(code)
        title = anchor.get_text(strip=True)
        url = urljoin(_TEMPO_BASE, href)
        results.append((code, title, url))

    return results


def extract_event_dates(
    html: str,
    *,
    today: Optional[date] = None,
) -> List[Tuple[str, datetime]]:
    """Parse the EventDateID select into ``(date_id, naive datetime)`` tuples.

    Skips the placeholder option (``value='0'`` / empty text) and any option
    whose text does not parse. ``date_past`` divs are not in the select, so no
    past-date filtering is needed. The returned datetimes are naive local times
    (the caller attaches the club timezone).
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", attrs={"name": "EventDateID"})
    if select is None:
        return []

    ref = today or date.today()
    results: List[Tuple[str, datetime]] = []

    for option in select.find_all("option"):
        date_id = (option.get("value") or "").strip()
        if not date_id or date_id == "0":
            continue
        parsed = _parse_option_datetime(option.get_text(strip=True), ref)
        if parsed is not None:
            results.append((date_id, parsed))

    return results


def _parse_option_datetime(text: str, ref: date) -> Optional[datetime]:
    """Parse 'Fri Jun 26 @ 7:30pm (...)' into a datetime, inferring the year."""
    match = _OPTION_RE.search(text or "")
    if not match:
        return None

    month = _MONTHS.get(match.group("mon").lower())
    if month is None:
        return None

    day = int(match.group("day"))
    hour = int(match.group("hour")) % 12
    if match.group("ampm").lower() == "pm":
        hour += 12
    minute = int(match.group("minute"))

    year = _infer_year(month, day, ref)
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def _infer_year(month: int, day: int, ref: date) -> int:
    """Pick the year so the month/day lands on/after (ref - slack)."""
    candidate = ref.year
    try:
        if date(candidate, month, day) < ref - timedelta(days=_ROLLOVER_SLACK_DAYS):
            candidate += 1
    except ValueError:
        # Feb 29 in a non-leap candidate year, etc. — fall back to next year.
        candidate += 1
    return candidate
