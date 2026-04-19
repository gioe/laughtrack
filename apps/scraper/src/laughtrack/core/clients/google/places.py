"""Google Places API (New) client — single-request venue hours lookup.

Uses a single ``places:searchText`` POST with a field mask that asks for
``regularOpeningHours.weekdayDescriptions`` on the top-level ``places[*]``
node so the place_id and the human-readable hours come back in one round-
trip (no separate ``places/{id}`` details call).  Parses the returned
``weekdayDescriptions`` strings into the project's canonical hours shape:
``Record<lowercase day, compact range>`` — e.g. ``{"monday": "5pm-11pm"}``.

Pricing: Text Search with the opening-hours field currently bills under the
"Text Search Pro" SKU (~$32 per 1k requests as of 2025).  A one-shot
backfill of ~340 clubs is well under $20.

Docs: https://developers.google.com/maps/documentation/places/web-service/text-search
"""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from laughtrack.foundation.infrastructure.logger.logger import Logger

_API_URL = "https://places.googleapis.com/v1/places:searchText"

_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.regularOpeningHours.weekdayDescriptions"
)

# "Monday: 5:00 PM – 11:00 PM" / "Tuesday: Closed" / "Wednesday: Open 24 hours"
_DAY_PREFIX_RE = re.compile(
    r"^\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)

# "5:00 PM – 11:00 PM" — en dash or hyphen, tolerant of thin/narrow-nbsp before AM/PM
_TIME_RANGE_RE = re.compile(
    r"^\s*(\d{1,2})(?::(\d{2}))?\s*([AP]M)\s*[\u2013\u2014\-]\s*"
    r"(\d{1,2})(?::(\d{2}))?\s*([AP]M)\s*$",
    re.IGNORECASE,
)

_ALWAYS_OPEN_PHRASES = frozenset({"open 24 hours", "24 hours", "24/7"})


@dataclass
class PlacesHoursResult:
    """Outcome of one ``fetch_hours`` call.

    ``place_id`` is returned even when parsing fails so callers can cache
    the identifier for future refreshes.  ``hours`` is ``None`` when the
    API returned no match, the match had no ``regularOpeningHours`` field,
    or every weekday entry failed to parse.
    """

    place_id: Optional[str]
    hours: Optional[Dict[str, str]]


def _normalize_ws(text: str) -> str:
    """Collapse thin / narrow-nbsp / regular nbsp into plain spaces and strip."""
    return (
        text.replace("\u202f", " ")  # narrow no-break space (Google uses this before AM/PM)
        .replace("\u2009", " ")  # thin space
        .replace("\u00a0", " ")  # no-break space
        .strip()
    )


def _format_12h(hour: int, minutes: int, ampm: str) -> str:
    suffix = ampm.lower()
    if minutes:
        return f"{hour}:{minutes:02d}{suffix}"
    return f"{hour}{suffix}"


def parse_weekday_descriptions(descriptions: List[str]) -> Optional[Dict[str, str]]:
    """Convert Places ``weekdayDescriptions`` into the project hours shape.

    Returns ``None`` when no entry parses.  Entries that say "Closed" are
    intentionally omitted from the result (matches existing behaviour:
    JSON-LD extraction also omits closed days rather than writing an
    explicit "closed" marker).  "Open 24 hours" collapses to ``"24hrs"``.
    """
    if not descriptions:
        return None
    out: Dict[str, str] = {}
    for raw in descriptions:
        if not isinstance(raw, str):
            continue
        line = _normalize_ws(raw)
        prefix = _DAY_PREFIX_RE.match(line)
        if not prefix:
            continue
        day = prefix.group(1).lower()
        rest = _normalize_ws(prefix.group(2))
        lowered = rest.lower()
        if lowered == "closed":
            continue
        if lowered in _ALWAYS_OPEN_PHRASES:
            out[day] = "24hrs"
            continue
        range_match = _TIME_RANGE_RE.match(rest)
        if not range_match:
            continue
        open_str = _format_12h(
            int(range_match.group(1)),
            int(range_match.group(2) or 0),
            range_match.group(3),
        )
        close_str = _format_12h(
            int(range_match.group(4)),
            int(range_match.group(5) or 0),
            range_match.group(6),
        )
        out[day] = f"{open_str}-{close_str}"
    return out or None


class GooglePlacesClient:
    """Client for Google Places API (New) text-search + hours lookup."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
        self._calls_made = 0
        # Guards _calls_made under concurrent ``asyncio.to_thread`` workers —
        # the enrichment script dispatches up to 8 in parallel, and a
        # naive ``+= 1`` would race past the daily cap by a handful of calls.
        self._counter_lock = threading.Lock()
        try:
            self._daily_limit = int(os.environ.get("GOOGLE_PLACES_DAILY_LIMIT", "500"))
        except ValueError:
            self._daily_limit = 500
        try:
            self._delay_s = float(os.environ.get("GOOGLE_PLACES_DELAY_S", "0.15"))
        except ValueError:
            self._delay_s = 0.15
        try:
            self._timeout_s = float(os.environ.get("GOOGLE_PLACES_TIMEOUT_S", "10"))
        except ValueError:
            self._timeout_s = 10.0

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def calls_made(self) -> int:
        return self._calls_made

    @property
    def calls_remaining(self) -> int:
        return max(0, self._daily_limit - self._calls_made)

    def _reserve_call_slot(self) -> bool:
        """Atomically check the cap and reserve a slot if room remains.

        Returning ``True`` commits the slot — the caller MUST proceed to
        make the HTTP request, since the increment is already accounted
        for.  Returning ``False`` means the cap was hit; do not call the
        API.  Holding the lock around both check and increment is what
        makes the cap a hard ceiling under concurrent workers.
        """
        with self._counter_lock:
            if self._calls_made >= self._daily_limit:
                return False
            self._calls_made += 1
            return True

    def _release_call_slot(self) -> None:
        """Roll back a reserved slot when the request never reached the API."""
        with self._counter_lock:
            if self._calls_made > 0:
                self._calls_made -= 1

    def fetch_hours(self, query: str) -> PlacesHoursResult:
        """Run a text search + hours fetch for ``query`` in one request.

        ``query`` should be a disambiguated venue string, e.g.
        ``"Comedy Cellar, New York, NY"``.  Returns an empty
        ``PlacesHoursResult(None, None)`` on any error, quota breach,
        missing key, empty results, or unparseable hours.
        """
        empty = PlacesHoursResult(None, None)
        if not self.is_configured:
            return empty
        if not query or not query.strip():
            return empty
        if not self._reserve_call_slot():
            Logger.warn(
                f"[places] daily limit reached ({self._daily_limit}) — skipping query '{query}'"
            )
            return empty

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }
        # pageSize=1 keeps the response small; we only ever use the top match.
        payload: Dict[str, Any] = {"textQuery": query, "pageSize": 1}

        if self._delay_s > 0:
            time.sleep(self._delay_s)

        try:
            resp = requests.post(
                _API_URL, json=payload, headers=headers, timeout=self._timeout_s
            )
        except requests.RequestException as exc:
            # Refund the reserved slot — no request reached the API, so a
            # transient outage shouldn't drain the daily quota.
            self._release_call_slot()
            Logger.warn(f"[places] request failed for '{query}': {exc}")
            return empty

        if resp.status_code == 429:
            Logger.warn(f"[places] rate limited (HTTP 429) on '{query}'")
            return empty
        if resp.status_code != 200:
            Logger.warn(
                f"[places] HTTP {resp.status_code} on '{query}': {resp.text[:200]}"
            )
            return empty

        try:
            data = resp.json()
        except ValueError as exc:
            Logger.warn(f"[places] bad JSON on '{query}': {exc}")
            return empty

        places = data.get("places") if isinstance(data, dict) else None
        if not isinstance(places, list) or not places:
            return empty
        top = places[0]
        if not isinstance(top, dict):
            return empty

        place_id = top.get("id") if isinstance(top.get("id"), str) else None
        opening = top.get("regularOpeningHours")
        descriptions: List[str] = []
        if isinstance(opening, dict):
            raw_descs = opening.get("weekdayDescriptions")
            if isinstance(raw_descs, list):
                descriptions = [d for d in raw_descs if isinstance(d, str)]
        return PlacesHoursResult(place_id=place_id, hours=parse_weekday_descriptions(descriptions))
