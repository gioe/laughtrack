"""Extraction for the EventON (WordPress) admin-ajax calendar loader.

EventON 4.x serves its frontend calendar from
``/wp-admin/admin-ajax.php`` via ``action=eventon_init_load``. The loader only
returns events when sent the full default shortcode (``sc``) parameter set as a
POST body — a minimal set yields an empty ``cals``. The response carries the
events under ``cals.<cal_id>.json`` as objects with ``event_id``,
``event_title`` and ``event_start_unix`` (local wall-clock encoded as UTC).

Per-event permalinks and taxonomy terms are not in the loader payload; they are
joined from the WP REST API (``/wp-json/wp/v2/ajde_events?include=<ids>``).
Comedy filtering uses the ``event_type`` taxonomy term id, discovered by name
from ``/wp-json/wp/v2/event_type``.

These are pure functions: JSON in, ``EventONEvent`` out. The scraper handles
HTTP.
"""

from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode

from laughtrack.core.entities.event.eventon import EventONEvent

# Default EventON shortcode params required for eventon_init_load to return
# events. event_past_future=future + hide_past=yes restrict to upcoming; the
# remaining flags are EventON's stock calendar defaults (a trimmed-but-complete
# set — the loader returns empty cals when the sc array is too sparse).
_DEFAULT_SC: Dict[str, str] = {
    "accord": "no",
    "bottom_nav": "no",
    "cal_id": "MAIN",
    "cal_init_nonajax": "no",
    "calendar_type": "default",
    "ep_fields": "",
    "etc_override": "no",
    "evc_open": "no",
    "event_count": "300",
    "event_location": "all",
    "event_order": "ASC",
    "event_organizer": "all",
    "event_parts": "no",
    "event_past_future": "future",
    "event_status": "all",
    "event_tag": "all",
    "event_type": "all",
    "event_type_2": "all",
    "event_virtual": "all",
    "eventtop_style": "2",
    "filter_relationship": "AND",
    "filter_type": "default",
    "filters": "yes",
    "fixed_month": "0",
    "fixed_year": "0",
    "ft_event_priority": "no",
    "hide_arrows": "no",
    "hide_cancels": "no",
    "hide_empty_months": "no",
    "hide_end_time": "no",
    "hide_month_headers": "no",
    "hide_mult_occur": "no",
    "hide_past": "yes",
    "hide_past_by": "ee",
    "lang": "L1",
    "number_of_months": "12",
    "sort_by": "sort_date",
    "ux_val": "0",
    "_cver": "4.0.6",
}


def build_loader_body(cal_id: str = "MAIN", overrides: Optional[Dict[str, str]] = None) -> str:
    """Build the urlencoded POST body for the eventon_init_load loader.

    Emits ``cals[<cal_id>][sc][<key>]=<value>`` pairs for the full default
    shortcode param set (with optional *overrides* merged in) plus the action.
    """
    sc = dict(_DEFAULT_SC)
    sc["cal_id"] = cal_id
    if overrides:
        sc.update(overrides)

    pairs = [("action", "eventon_init_load")]
    for key, value in sc.items():
        pairs.append((f"cals[{cal_id}][sc][{key}]", value))
    return urlencode(pairs)


def parse_loader_events(loader_json: Any, cal_id: str = "MAIN") -> List[Dict[str, Any]]:
    """Return the raw future-event dicts from a loader response.

    Drops occurrences flagged ``event_past == 'yes'`` defensively (the loader is
    asked for future events, but guard anyway).
    """
    if not isinstance(loader_json, dict):
        return []
    cals = loader_json.get("cals")
    if not isinstance(cals, dict):
        return []
    cal = cals.get(cal_id) or cals.get(f"evcal_calendar_{cal_id}")
    if not isinstance(cal, dict):
        # Fall back to the first calendar present.
        cal = next((c for c in cals.values() if isinstance(c, dict)), None)
    if not isinstance(cal, dict):
        return []
    events = cal.get("json")
    if not isinstance(events, list):
        return []
    return [e for e in events if isinstance(e, dict) and e.get("event_past") != "yes"]


def discover_term_ids(
    terms: List[Dict[str, Any]],
    target_names: tuple = ("comedy",),
) -> Set[int]:
    """Return ``event_type`` term ids whose name/slug matches *target_names*.

    Case-insensitive substring match on both ``name`` and ``slug``.
    """
    targets = tuple(t.lower() for t in target_names)
    ids: Set[int] = set()
    for term in terms or []:
        haystack = f"{term.get('name', '')} {term.get('slug', '')}".lower()
        if any(t in haystack for t in targets):
            tid = term.get("id")
            if isinstance(tid, int):
                ids.add(tid)
    return ids


def build_rest_meta(rest_items: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Index WP REST ajde_events items by post id → {link, event_type[ids]}."""
    meta: Dict[int, Dict[str, Any]] = {}
    for item in rest_items or []:
        pid = item.get("id")
        if isinstance(pid, int):
            meta[pid] = {
                "link": item.get("link") or "",
                "event_type": item.get("event_type") or [],
            }
    return meta


def extract_events(
    loader_events: List[Dict[str, Any]],
    rest_meta: Dict[int, Dict[str, Any]],
    comedy_term_ids: Optional[Set[int]] = None,
) -> List[EventONEvent]:
    """Build EventONEvents, joining permalinks from *rest_meta*.

    When *comedy_term_ids* is non-empty, keep only events whose REST
    ``event_type`` includes one of those term ids. An event with no REST entry
    (no permalink) is dropped — Show requires a page URL.
    """
    events: List[EventONEvent] = []
    for raw in loader_events:
        event_id = raw.get("event_id") or raw.get("ID")
        title = (raw.get("event_title") or "").strip()
        start_unix = raw.get("event_start_unix")
        if not event_id or not title or not start_unix:
            continue

        meta = rest_meta.get(int(event_id))
        if not meta or not meta.get("link"):
            continue

        if comedy_term_ids:
            term_ids = set(meta.get("event_type") or [])
            if not (term_ids & comedy_term_ids):
                continue

        events.append(
            EventONEvent(
                title=title,
                start_unix=int(start_unix),
                show_page_url=meta["link"],
            )
        )
    return events
