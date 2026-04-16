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
import re
from typing import List

# window.dataLayer.push({...}) is the canonical listing-page payload. The JSON
# object is single-line; we capture the braced body, parse it, and pull out
# event_ids. Using a JSON parser (rather than a naive array regex) guards
# against malformed matches when TicketLeap emits multiple dataLayer calls or
# reformats the payload.
_DATA_LAYER_PUSH_RE = re.compile(r"dataLayer\.push\((\{.*?\})\)", re.DOTALL)


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

    for match in _DATA_LAYER_PUSH_RE.finditer(html_content):
        payload_text = match.group(1)
        try:
            payload = json.loads(payload_text)
        except (ValueError, TypeError):
            continue

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
