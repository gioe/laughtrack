"""TicketLeap listing-page event ID extractor.

The TicketLeap public listing page (events.ticketleap.com/events/{org_slug})
does NOT include per-event JSON-LD on the listing itself. Instead, it emits a
dataLayer.push() call that carries the full list of event IDs:

    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({"event":"orglisting_page_view", ...,
                           "event_ids":[2053571, 2091519, ...],
                           ...})

This module extracts that integer array so the scraper can then visit each
event detail page (events.ticketleap.com/event/{id}) to parse its JSON-LD.
"""

from __future__ import annotations

import json
from typing import List

# Marker scanned at every offset in the HTML. From each match we hand the
# payload body to JSONDecoder.raw_decode, which uses the JSON grammar to find
# the closing brace — so a literal '})' inside a string value cannot truncate
# the payload the way a non-greedy regex would.
_PUSH_MARKER = "dataLayer.push("

_DECODER = json.JSONDecoder()


def extract_event_ids(html_content: str) -> List[int]:
    """Return event IDs from a TicketLeap org listing page.

    Scans every dataLayer.push JSON payload in the HTML and returns the union
    of their `event_ids` arrays (deduplicated, order-preserving). Returns [] if
    no payload is present or none carry event IDs.
    """
    if not html_content:
        return []

    seen: set[int] = set()
    ordered: List[int] = []

    search_from = 0
    while True:
        marker_idx = html_content.find(_PUSH_MARKER, search_from)
        if marker_idx == -1:
            break

        payload_start = marker_idx + len(_PUSH_MARKER)
        # Skip whitespace between '(' and the payload's opening brace so
        # reformatted HTML ("push( { ... })") still parses.
        while (
            payload_start < len(html_content)
            and html_content[payload_start].isspace()
        ):
            payload_start += 1

        # Advance past this marker even when the payload is unparseable so we
        # never re-enter the same branch on the next iteration.
        search_from = payload_start

        if payload_start >= len(html_content) or html_content[payload_start] != "{":
            continue

        try:
            payload, end = _DECODER.raw_decode(html_content, payload_start)
        except json.JSONDecodeError:
            continue

        search_from = end

        if not isinstance(payload, dict):
            continue

        ids = payload.get("event_ids")
        if not isinstance(ids, list):
            continue

        for raw_id in ids:
            try:
                event_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if event_id in seen:
                continue
            seen.add(event_id)
            ordered.append(event_id)

    return ordered


def build_event_detail_url(event_id: int) -> str:
    """Build a canonical TicketLeap event detail URL from an event ID."""
    return f"https://events.ticketleap.com/event/{event_id}"
