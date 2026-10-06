"""Strict, page-bound producer inventory extracted from PunchUp hydration."""

import json
import re
from dataclasses import dataclass

from laughtrack.core.clients.rsc.extractor import extract_balanced, extract_push_payloads


@dataclass
class PunchupInventory:
    events: list
    locations: list
    errors: list


def merge_events(events):
    """Deduplicate native IDs; conflicting occurrence identities are held."""
    by_id, conflicts, errors = {}, set(), []
    fields = ("title", "datetime", "ticket_link", "venue_id", "venue", "location", "tixologi_event_id")
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("id"), str) or not event["id"]:
            errors.append("Malformed native show identity")
            continue
        ident = event["id"]
        if ident in by_id and any(by_id[ident].get(k) != event.get(k) for k in fields):
            conflicts.add(ident)
        else:
            by_id[ident] = event
    for ident in sorted(conflicts):
        by_id.pop(ident, None)
        errors.append(f"Conflicting native show {ident}")
    return list(by_id.values()), errors


def extract_inventory(html, page_id, slug):
    """Read complete query objects, never attach a neighboring query's data."""
    queries = []
    for payload in extract_push_payloads(html):
        for match in re.finditer(r'"queries"\s*:\s*\[', payload):
            raw = extract_balanced(payload, match.end() - 1, "[", "]")
            try:
                queries.extend(json.loads(raw))
            except (ValueError, TypeError):
                raise ValueError("Malformed PunchUp query state")
    locations, events, found_page, found_shows = {}, [], False, False
    for query in queries:
        if not isinstance(query, dict):
            continue
        key = query.get("queryKey")
        if not isinstance(key, list) or len(key) < 2:
            continue
        data = (query.get("state") or {}).get("data")
        if key == ["venue-page", slug]:
            if not isinstance(data, dict) or data.get("id") != page_id or not isinstance(data.get("locations"), list):
                raise ValueError("PunchUp source page/location identity mismatch")
            found_page = True
            for loc in data["locations"]:
                if not isinstance(loc, dict) or not loc.get("id"):
                    raise ValueError("Malformed PunchUp location")
                if loc["id"] in locations and locations[loc["id"]] != loc:
                    raise ValueError("Conflicting PunchUp locations")
                locations[loc["id"]] = loc
        elif key[0] == "venueShows" and key[1] == page_id:
            if not isinstance(data, list):
                raise ValueError("Malformed PunchUp shows query")
            found_shows = True
            events.extend(data)
        elif key[:3] == ["venuePageCarousel", page_id, "public"]:
            if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                raise ValueError("Malformed PunchUp carousel")
            for item in data["items"]:
                if isinstance(item, dict) and item.get("type") == "show":
                    events.append(item.get("show"))
    if not found_page or not found_shows:
        raise ValueError("Missing source-bound PunchUp page/shows query")
    events, errors = merge_events(events)
    return PunchupInventory(events, list(locations.values()), errors)
