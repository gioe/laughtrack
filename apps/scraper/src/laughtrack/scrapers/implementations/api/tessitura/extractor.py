"""Extraction for the Tessitura WordPress REST feed.

Tessitura venue operators that run the WordPress integration plugin expose:
  * ``/wp-json/wp/v2/genre`` — a taxonomy whose terms include "Comedy".
  * ``/wp-json/wp/v2/tessi_production?genre={id}`` — comedy productions, each
    with ``title.rendered`` and a ``content.rendered`` HTML blob that embeds the
    primary showtime ("Saturday, December 5, 2026 | 7 PM"), the venue/room name
    ("Davidson Theatre, Riffe Center"), and the box-office purchase URL
    (``https://tickets.{org}.com/{prod}/{perf}/``).

These are pure functions: JSON in, ``TessituraEvent`` out. The scraper handles
fetching and pagination.
"""

import re
from html import unescape
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.tessitura import TessituraEvent

# Primary showtime, e.g. "Saturday, December 5, 2026 | 7 PM" or "... | 7:30 PM".
_SHOWTIME_RE = re.compile(
    r"(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),\s+"
    r"[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s*\|\s*\d{1,2}(?::\d{2})?\s*[AP]M"
)

# Box-office purchase URL on any tickets.{org} host, e.g.
# "https://tickets.capa.com/11600/11601/".
_TICKET_URL_RE = re.compile(r"https?://tickets\.[a-z0-9.-]+/[0-9]+(?:/[0-9]+)?/?")

# Venue/room name sits between a "VENUE" label and the next section label.
_VENUE_RE = re.compile(
    r"VENUE\s+(.+?)\s+(?:Plan Your Visit|Description|VENUE|$)",
    re.IGNORECASE,
)

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    """Collapse an HTML blob to single-spaced plain text."""
    return " ".join(unescape(_TAG_RE.sub(" ", html or "")).split())


def discover_comedy_genre_ids(
    genre_terms: List[Dict[str, Any]],
    target_names: tuple = ("comedy",),
) -> List[int]:
    """Return the genre term id(s) whose name matches one of *target_names*.

    Matching is case-insensitive and substring-based so "Stand-Up Comedy" also
    matches "comedy". Terms with a zero ``count`` are skipped (no productions).
    """
    targets = tuple(t.lower() for t in target_names)
    ids: List[int] = []
    for term in genre_terms or []:
        name = str(term.get("name", "")).lower()
        if any(t in name for t in targets) and term.get("count", 0):
            term_id = term.get("id")
            if isinstance(term_id, int):
                ids.append(term_id)
    return ids


def _rendered(field: Any) -> str:
    """Read a WP ``{"rendered": "..."}`` field, tolerating a bare string."""
    if isinstance(field, dict):
        return str(field.get("rendered", ""))
    return str(field or "")


def extract_event(production: Dict[str, Any]) -> Optional[TessituraEvent]:
    """Build a TessituraEvent from one ``tessi_production`` REST record.

    Returns None when the record lacks a parseable title or showtime.
    """
    title = _strip_html(_rendered(production.get("title")))
    if not title:
        return None

    content = _rendered(production.get("content"))
    text = _strip_html(content)

    showtime_match = _SHOWTIME_RE.search(text)
    if not showtime_match:
        return None
    start_date_str = showtime_match.group(0)

    show_page_url = str(production.get("link") or "").strip()
    if not show_page_url:
        return None

    ticket_match = _TICKET_URL_RE.search(content)
    ticket_url = ticket_match.group(0) if ticket_match else None

    venue_match = _VENUE_RE.search(text)
    venue_name = venue_match.group(1).strip() if venue_match else None

    return TessituraEvent(
        title=title,
        start_date_str=start_date_str,
        show_page_url=show_page_url,
        ticket_url=ticket_url,
        venue_name=venue_name,
    )


def extract_events(productions: List[Dict[str, Any]]) -> List[TessituraEvent]:
    """Map a page of ``tessi_production`` records to TessituraEvents.

    Records that cannot be parsed (missing title/showtime) are dropped.
    """
    events: List[TessituraEvent] = []
    for production in productions or []:
        event = extract_event(production)
        if event is not None:
            events.append(event)
    return events
