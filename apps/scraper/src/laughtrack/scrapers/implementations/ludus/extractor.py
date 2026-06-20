"""Parsers for Ludus (ludus.com) box-office HTML.

Two page types, both behind a Cloudflare managed challenge (cleared with
curl_cffi impersonation):

1. **Embed** ``{subdomain}.ludus.com/embed/index.php?widget=1&sections=all&hideNav=false``
   — one ``div.show_item[data-show-id][data-event-categories]`` per show, with
   the title in ``h2.show_item_title``. Comedy shows carry a venue-specific
   category id in the semicolon-separated ``data-event-categories`` (e.g. ``468;``
   for Park Theatre). The ``&category_id=`` URL param does NOT server-side filter,
   so filtering is client-side on this attribute.

2. **Detail** ``{subdomain}.ludus.com/index.php?show_id=<id>`` — dates are NOT on
   the embed cards; each detail page lists ``div.showtimes_item[data-past-date]``
   rows with a human-readable "Sunday, July 12, 2026 7:00 PM" date.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Tuple

from bs4 import BeautifulSoup

# "Sunday, July 12, 2026 7:00 PM"
_SHOWTIME_RE = re.compile(
    r"(?P<mon>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})\s+(?P<ampm>[AP]M)",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def embed_url_for_subdomain(subdomain: str) -> str:
    """Box-office embed URL for a Ludus venue subdomain."""
    return (
        f"https://{subdomain}.ludus.com/embed/index.php"
        "?widget=1&sections=all&hideNav=false"
    )


def detail_url_for_show(subdomain: str, show_id: str) -> str:
    """Per-show detail URL for a Ludus venue subdomain."""
    return f"https://{subdomain}.ludus.com/index.php?show_id={show_id}"


def extract_comedy_cards(html: str, category_id: str) -> List[Tuple[str, str]]:
    """Return ``(show_id, title)`` for embed cards tagged with ``category_id``.

    Title is taken from ``h2.show_item_title`` and trimmed at the venue-name
    separator (the listing appends " ★ <Venue>" to every card title).
    """
    if not html or not category_id:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results: List[Tuple[str, str]] = []
    for card in soup.select("div.show_item"):
        cats = [c.strip() for c in (card.get("data-event-categories") or "").split(";") if c.strip()]
        if category_id not in cats:
            continue
        show_id = (card.get("data-show-id") or "").strip()
        if not show_id:
            continue
        title_el = card.select_one("h2.show_item_title") or card.select_one(".show_item_title")
        title = _clean_title(title_el.get_text(" ", strip=True) if title_el else "")
        results.append((show_id, title))
    return results


def extract_showtimes(html: str) -> List[datetime]:
    """Parse a detail page's upcoming showtimes into naive datetimes.

    Skips rows flagged ``data-past-date="1"``. Deduplicates (the showtime row
    repeats its date text internally).
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    seen: set = set()
    out: List[datetime] = []
    for item in soup.select("div.showtimes_item"):
        if (item.get("data-past-date") or "").strip() == "1":
            continue
        dt = _parse_showtime(item.get_text(" ", strip=True))
        if dt is not None and dt not in seen:
            seen.add(dt)
            out.append(dt)
    return out


def _clean_title(raw: str) -> str:
    """Trim the trailing ' ★ <Venue>…' decoration from an embed card title."""
    if not raw:
        return ""
    # Cut at the first star separator the listing inserts before the venue name.
    title = re.split(r"\s*★\s*", raw, maxsplit=1)[0]
    return title.strip()


def _parse_showtime(text: str):
    match = _SHOWTIME_RE.search(text or "")
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
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None
