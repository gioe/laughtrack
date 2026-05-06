"""TicketLeap listing-page event ID extractor.

The TicketLeap public listing page (events.ticketleap.com/events/{org_slug})
serializes the visible events into different inline-JS containers depending on
the page version:

1. (legacy) ``window.dataLayer.push({"event":"orglisting_page_view", ...,
   "event_ids":[2053571, 2091519, ...], ...})``
2. (current, observed 2026-05) ``AppWrapper.default(
   document.getElementById('listing'), {<config>}, {<seller>},
   [{..., "event_id": <int>, ...}, ...])`` — events live in one of the JSON
   arguments and each event object carries a singular ``event_id`` field.

Rather than chase whichever container TicketLeap is using this week, scan
every JSON object literal in the HTML and recursively pull out any
``event_id`` integers and any ``event_ids`` arrays we encounter. Brute-force
JSON scanning is cheap (~10 ms even on a fully-rendered Playwright page) and
shields the scraper from another silent-zero regression the next time the
listing template changes.
"""

from __future__ import annotations

import json
from typing import Any, List

_DECODER = json.JSONDecoder()


def extract_event_ids(html_content: str) -> List[int]:
    """Return event IDs from a TicketLeap org listing page.

    Scans every JSON object literal in the HTML and returns the deduplicated,
    order-preserving union of every ``event_ids`` array entry and every
    singular ``event_id`` field found while walking each parsed payload.
    Returns ``[]`` if no event IDs are found.
    """
    if not html_content:
        return []

    seen: set[int] = set()
    ordered: List[int] = []

    cursor = 0
    end_pos = len(html_content)
    while cursor < end_pos:
        if html_content[cursor] != "{":
            cursor += 1
            continue

        try:
            payload, end = _DECODER.raw_decode(html_content, cursor)
        except json.JSONDecodeError:
            cursor += 1
            continue

        _walk(payload, seen, ordered)
        cursor = end

    return ordered


def _walk(payload: Any, seen: set[int], ordered: List[int]) -> None:
    """Recursively pull ``event_id`` ints and ``event_ids`` arrays from a payload."""
    if isinstance(payload, dict):
        ids = payload.get("event_ids")
        if isinstance(ids, list):
            for raw in ids:
                _add(raw, seen, ordered)
        eid = payload.get("event_id")
        if eid is not None and not isinstance(eid, (dict, list)):
            _add(eid, seen, ordered)
        for value in payload.values():
            _walk(value, seen, ordered)
    elif isinstance(payload, list):
        for item in payload:
            _walk(item, seen, ordered)


def _add(raw: Any, seen: set[int], ordered: List[int]) -> None:
    try:
        event_id = int(raw)
    except (TypeError, ValueError):
        return
    if event_id in seen:
        return
    seen.add(event_id)
    ordered.append(event_id)


def build_event_detail_url(event_id: int) -> str:
    """Build a canonical TicketLeap event detail URL from an event ID."""
    return f"https://events.ticketleap.com/event/{event_id}"
