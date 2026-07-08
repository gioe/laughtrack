#!/usr/bin/env python3
"""Backfill missing club google_place_id from Google Places (TASK-3174).

discover-nearby's strongest dedup arm is the exact ``google_place_id`` match, but
legacy clubs with ``google_place_id=NULL`` silently miss that arm and fall back to
the weaker name/address arms. This script resolves and backfills a place_id on
existing clubs that currently have NULL, using a single Google Places Text Search
per club keyed on name + address/city/state/zip.

Dry-run by default. Only writes a place_id for active, visible physical venue rows
(``club_type='club'``), and only on a **high-confidence** match (state +
zip-or-street-number + name-token overlap). The UPDATE is guarded by
``google_place_id IS NULL`` so re-runs are idempotent and never overwrite an
existing place_id. Sibling of the TASK-3032 coordinate backfill, which only
processed coord-missing rows and so left coord-present / place_id-NULL clubs
untouched.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from psycopg2.extras import RealDictCursor, execute_values

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction  # noqa: E402

_TASK_ID = 3174
_DESCRIPTION_MARKER = "TASK-3174 place_id backfill:"
_API_BASE = "https://places.googleapis.com/v1"
_TEXT_SEARCH_URL = f"{_API_BASE}/places:searchText"
_TEXT_SEARCH_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.websiteUri,"
    "places.primaryType"
)
_WORD_RE = re.compile(r"[a-z0-9]+")
_STATE_RE = re.compile(r"\b[A-Z]{2}\b")
_WEAK_NAME_TOKENS = {
    "a", "an", "and", "at", "club", "comedy", "event", "events", "improv", "live",
    "lounge", "near", "night", "room", "shows", "the", "theater", "theatre", "us",
}
_NON_VENUE_PATTERNS = (
    re.compile(r"\broving producer\b", re.I),
    re.compile(r"\bfestival based\b", re.I),
    re.compile(r"\bsecret location\b", re.I),
    re.compile(r"\bbooking details\b", re.I),
    re.compile(r"\btour dates?\b", re.I),
)


@dataclass(frozen=True)
class ClubRow:
    id: int
    name: str
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    country: str | None
    website: str | None
    status: str
    visible: bool
    club_type: str
    google_place_id: str | None


@dataclass(frozen=True)
class PlaceResult:
    source: str
    place_id: str
    display_name: str | None
    formatted_address: str | None
    city: str | None
    state_code: str | None
    lat: float | None
    lng: float | None
    website: str | None
    primary_type: str | None


@dataclass(frozen=True)
class AuditRow:
    club: ClubRow
    eligible: bool
    query: str | None
    result: PlaceResult | None
    accepted: bool
    reason: str


class PlacesQuota:
    def __init__(self, *, api_key: str, limit: int, delay_s: float, timeout_s: float) -> None:
        self.api_key = api_key
        self.limit = limit
        self.delay_s = delay_s
        self.timeout_s = timeout_s
        self.calls_made = 0

    def reserve(self) -> bool:
        if self.calls_made >= self.limit:
            return False
        self.calls_made += 1
        if self.delay_s > 0:
            time.sleep(self.delay_s)
        return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill clubs.google_place_id from Google Places (TASK-3174). Dry-run by default."
    )
    parser.add_argument("--apply", action="store_true", help="Write accepted place_ids to the DB.")
    parser.add_argument("--dry-run", action="store_true", help="Print/report only; this is the default.")
    parser.add_argument("--json", type=Path, default=None, help="Write full audit JSON to this path.")
    parser.add_argument("--limit", type=int, default=None, help="Resolve at most N eligible rows.")
    parser.add_argument("--club-ids", nargs="+", type=int, default=None, help="Restrict to explicit club IDs.")
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Maximum Google Places HTTP requests; defaults to GOOGLE_PLACES_DAILY_LIMIT.",
    )
    return parser.parse_args()


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _tokens(value: str | None) -> set[str]:
    return {token for token in _WORD_RE.findall((value or "").lower()) if token not in _WEAK_NAME_TOKENS}


def _normalize_state(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().upper()
    return value if re.fullmatch(r"[A-Z]{2}", value) else None


def _extract_state_from_address(address: str | None) -> str | None:
    if not address:
        return None
    matches = _STATE_RE.findall(address)
    return matches[-1] if matches else None


def _extract_components(data: dict[str, Any]) -> tuple[str | None, str | None]:
    state_code: str | None = None
    city: str | None = None
    components = data.get("addressComponents")
    if isinstance(components, list):
        for component in components:
            if not isinstance(component, dict):
                continue
            types = component.get("types")
            if not isinstance(types, list):
                continue
            if state_code is None and "administrative_area_level_1" in types:
                short = component.get("shortText")
                if isinstance(short, str) and short:
                    state_code = short
            if city is None and "locality" in types:
                name = component.get("shortText") or component.get("longText")
                if isinstance(name, str) and name:
                    city = name
    return city, state_code


def _display_name(place: dict[str, Any]) -> str | None:
    display = place.get("displayName")
    if isinstance(display, dict) and isinstance(display.get("text"), str):
        return display["text"]
    return None


def _location(place: dict[str, Any]) -> tuple[float | None, float | None]:
    raw = place.get("location")
    if not isinstance(raw, dict):
        return None, None
    lat = raw.get("latitude")
    lng = raw.get("longitude")
    return (
        float(lat) if isinstance(lat, (int, float)) else None,
        float(lng) if isinstance(lng, (int, float)) else None,
    )


def _place_result_from_payload(source: str, place_id: str, payload: dict[str, Any]) -> PlaceResult:
    lat, lng = _location(payload)
    address = payload.get("formattedAddress")
    formatted_address = address if isinstance(address, str) and address else None
    city, state_code = _extract_components(payload)
    if state_code is None:
        state_code = _extract_state_from_address(formatted_address)
    website = payload.get("websiteUri")
    primary_type = payload.get("primaryType")
    return PlaceResult(
        source=source,
        place_id=place_id,
        display_name=_display_name(payload),
        formatted_address=formatted_address,
        city=city,
        state_code=state_code,
        lat=lat,
        lng=lng,
        website=website if isinstance(website, str) and website else None,
        primary_type=primary_type if isinstance(primary_type, str) and primary_type else None,
    )


def _load_rows(cur: RealDictCursor, club_ids: list[int] | None) -> list[ClubRow]:
    filters = ["c.google_place_id IS NULL"]
    params: list[Any] = []
    if club_ids:
        filters.append("c.id = ANY(%s::int[])")
        params.append(club_ids)

    cur.execute(
        f"""
        SELECT
            c.id, c.name, c.address, c.city, c.state, c.zip_code, c.country, c.website,
            c.status, c.visible, c.club_type, c.google_place_id
        FROM clubs c
        WHERE {" AND ".join(f"({f})" for f in filters)}
        ORDER BY c.id
        """,
        tuple(params) if params else None,
    )
    return [
        ClubRow(
            id=row["id"],
            name=row["name"],
            address=row["address"],
            city=row["city"],
            state=row["state"],
            zip_code=row["zip_code"],
            country=row["country"],
            website=row["website"],
            status=row["status"],
            visible=bool(row["visible"]),
            club_type=row["club_type"],
            google_place_id=row["google_place_id"],
        )
        for row in cur.fetchall()
    ]


def _eligibility(row: ClubRow) -> tuple[bool, str]:
    if row.status != "active":
        return False, f"excluded {row.status} row"
    if not row.visible:
        return False, "excluded hidden row"
    if row.club_type != "club":
        return False, f"excluded club_type={row.club_type}"
    haystack = " ".join(part for part in (row.name, row.address, row.website) if part)
    for pattern in _NON_VENUE_PATTERNS:
        if pattern.search(haystack):
            return False, f"excluded non-venue pattern {pattern.pattern}"
    return True, "eligible physical venue club"


def _build_query(row: ClubRow) -> str:
    parts = [row.name, row.address, row.city, row.state, row.zip_code]
    if not any(part for part in (row.address, row.city, row.state, row.zip_code)):
        parts.append(row.website)
    return " ".join(str(part).strip() for part in parts if part and str(part).strip())


def _street_number(address: str | None) -> str | None:
    """Leading house number only.

    Anchored to the start of the address so a zip or suite/unit digit run later in
    the string cannot become a false street-number anchor.
    """
    if not address:
        return None
    match = re.match(r"\s*(\d{1,6})\b", address)
    return match.group(1) if match else None


def _result_zip(address: str | None) -> str | None:
    """The US ZIP from a Google formatted address.

    Prefers the 5-digit group that follows the 2-letter state code
    ("..., Brookfield, WI 53045, USA") so a LEADING 5-digit street number
    ("20110 W Bluemound Rd, Brookfield, WI 53045") is not mistaken for the zip —
    that artifact caused valid venues (Milwaukee Improv, several Funny Bones,
    arena addresses) to be false-rejected as zip mismatches. Falls back to the
    last 5-digit run when no state+zip pattern is present.
    """
    if not address:
        return None
    after_state = re.search(r"\b[A-Z]{2}\s+(\d{5})(?:-\d{4})?\b", address)
    if after_state:
        return after_state.group(1)
    runs = re.findall(r"\b(\d{5})\b", address)
    return runs[-1] if runs else None


def _validate(row: ClubRow, result: PlaceResult) -> tuple[bool, str]:
    """High-confidence acceptance gate for a text-search place_id match.

    Coordinates are not required (we only need the place_id), but a formatted
    address plus a state match and a zip-or-street-number anchor and a name-token
    overlap are required so a wrong place_id is never written onto a legacy club.
    """
    if not result.place_id:
        return False, "missing place id"
    if not result.formatted_address:
        return False, "missing formatted address"

    expected_state = _normalize_state(row.state)
    actual_state = _normalize_state(result.state_code)
    if expected_state and actual_state and expected_state != actual_state:
        return False, f"state mismatch: expected {expected_state}, got {actual_state}"

    # A zip present on BOTH sides that disagrees is a hard mismatch. A zip absent
    # from the result (Google sometimes omits it) is not — fall back to the
    # street-number anchor below.
    expected_zip = (row.zip_code or "").strip()[:5]
    result_zip = _result_zip(result.formatted_address)
    if expected_zip.isdigit() and result_zip and expected_zip != result_zip:
        return False, f"zip mismatch: expected {expected_zip}, got {result_zip}"
    zip_matches = bool(expected_zip.isdigit() and result_zip == expected_zip)

    row_street_number = _street_number(row.address)
    result_street_number = _street_number(result.formatted_address)
    street_number_matches = bool(
        row_street_number and result_street_number and row_street_number == result_street_number
    )

    # Require at least one strong address anchor (zip OR street number) so a
    # same-name venue in a different town can't be mis-linked.
    if not (zip_matches or street_number_matches):
        return False, "no zip or street-number anchor"

    row_tokens = _tokens(row.name)
    result_tokens = _tokens(result.display_name)
    overlap = row_tokens & result_tokens
    if row_tokens:
        if not overlap:
            return False, "no name-token overlap"
    elif not zip_matches:
        # A generic name (all weak tokens, e.g. "The Comedy Club") leaves no name
        # signal to verify the match, so require the stronger zip anchor rather
        # than accepting on a street-number-only match.
        return False, "generic name without zip anchor"

    return True, "accepted high-confidence text search match"


def _text_search(quota: PlacesQuota, query: str) -> tuple[PlaceResult | None, str | None]:
    if not query:
        return None, "missing search query"
    if not quota.reserve():
        return None, "skipped: Google Places request quota exhausted"
    try:
        response = requests.post(
            _TEXT_SEARCH_URL,
            json={"textQuery": query, "pageSize": 1},
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": quota.api_key,
                "X-Goog-FieldMask": _TEXT_SEARCH_FIELD_MASK,
            },
            timeout=quota.timeout_s,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        return None, f"text search failed: {exc}"
    places = data.get("places") if isinstance(data, dict) else None
    if not isinstance(places, list) or not places:
        return None, "no Google Places text search result"
    top = places[0]
    if not isinstance(top, dict):
        return None, "top Places result was not an object"
    place_id = top.get("id")
    if not isinstance(place_id, str) or not place_id:
        return None, "top Places result missing place id"
    return _place_result_from_payload("text_search", place_id, top), None


def _resolve_row(quota: PlacesQuota, row: ClubRow) -> AuditRow:
    eligible, eligibility_reason = _eligibility(row)
    if not eligible:
        return AuditRow(row, False, None, None, False, eligibility_reason)

    query = _build_query(row)
    result, error = _text_search(quota, query)
    if error:
        return AuditRow(row, True, query, result, False, error)
    if result is None:
        return AuditRow(row, True, query, None, False, "no Google Places result")

    accepted, reason = _validate(row, result)
    return AuditRow(row, True, query, result, accepted, reason)


def _description_note(row: AuditRow) -> str:
    result = row.result
    assert result is not None
    return f"{_DESCRIPTION_MARKER} place_id={result.place_id} resolved from Google Places text_search; {row.reason}"


def _write_accepted(cur: RealDictCursor, accepted: list[AuditRow]) -> int:
    values = []
    for row in accepted:
        result = row.result
        assert result is not None
        values.append((row.club.id, result.place_id, _description_note(row)))
    if not values:
        return 0

    cur.execute("""
        CREATE TEMP TABLE task_3174_place_id_backfill (
            club_id integer PRIMARY KEY,
            google_place_id text NOT NULL,
            note text NOT NULL
        ) ON COMMIT DROP
        """)
    execute_values(
        cur,
        """
        INSERT INTO task_3174_place_id_backfill (club_id, google_place_id, note)
        VALUES %s
        """,
        values,
    )
    cur.execute(
        """
        UPDATE clubs c
        SET google_place_id = b.google_place_id,
            description = CASE
                WHEN COALESCE(c.description, '') LIKE %s THEN c.description
                WHEN COALESCE(c.description, '') = '' THEN b.note
                ELSE c.description || E'\n\n' || b.note
            END
        FROM task_3174_place_id_backfill b
        WHERE c.id = b.club_id
          AND c.google_place_id IS NULL
        """,
        (f"%{_DESCRIPTION_MARKER}%",),
    )
    return int(cur.rowcount or 0)


def _missing_count(cur: RealDictCursor) -> int:
    cur.execute("SELECT COUNT(*) AS count FROM clubs WHERE google_place_id IS NULL")
    return int(cur.fetchone()["count"])


def _audit_payload(rows: list[AuditRow], before: int, after: int | None, calls_made: int) -> dict[str, Any]:
    accepted = [row for row in rows if row.accepted]
    rejected = [row for row in rows if row.eligible and not row.accepted]
    excluded = [row for row in rows if not row.eligible]
    return {
        "task_id": _TASK_ID,
        "missing_place_id_before": before,
        "missing_place_id_after": after,
        "google_places_calls_made": calls_made,
        "accepted_count": len(accepted),
        "rejected_or_unresolved_count": len(rejected),
        "excluded_count": len(excluded),
        "accepted": [
            {
                "club_id": row.club.id,
                "name": row.club.name,
                "place_id": row.result.place_id if row.result else None,
                "matched_name": row.result.display_name if row.result else None,
                "matched_address": row.result.formatted_address if row.result else None,
                "reason": row.reason,
            }
            for row in accepted
        ],
        "rejected_or_unresolved": [
            {
                "club": asdict(row.club),
                "query": row.query,
                "result": asdict(row.result) if row.result else None,
                "reason": row.reason,
            }
            for row in rejected
        ],
        "excluded": [
            {
                "club_id": row.club.id,
                "name": row.club.name,
                "club_type": row.club.club_type,
                "status": row.club.status,
                "visible": row.club.visible,
                "reason": row.reason,
            }
            for row in excluded
        ],
    }


def main() -> int:
    args = _parse_args()
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        print("GOOGLE_PLACES_API_KEY is not set; cannot resolve places.", file=sys.stderr)
        return 2

    request_limit = args.max_requests if args.max_requests is not None else _env_int("GOOGLE_PLACES_DAILY_LIMIT", 500)
    quota = PlacesQuota(
        api_key=api_key,
        limit=max(0, request_limit),
        delay_s=_env_float("GOOGLE_PLACES_DELAY_S", 0.15),
        timeout_s=_env_float("GOOGLE_PLACES_TIMEOUT_S", 10.0),
    )

    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            before = _missing_count(cur)
            rows = _load_rows(cur, args.club_ids)

    eligible_seen = 0
    audit_rows: list[AuditRow] = []
    for row in rows:
        eligible, _ = _eligibility(row)
        if eligible:
            if args.limit is not None and eligible_seen >= args.limit:
                audit_rows.append(AuditRow(row, True, None, None, False, "skipped by --limit"))
                continue
            eligible_seen += 1
        audit_rows.append(_resolve_row(quota, row))

    accepted = [row for row in audit_rows if row.accepted]
    updated = 0
    after = None
    if args.apply:
        with get_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                updated = _write_accepted(cur, accepted)
                after = _missing_count(cur)

    payload = _audit_payload(audit_rows, before, after, quota.calls_made)
    if args.json:
        args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Missing google_place_id before: {before}")
    if args.apply:
        print(f"Updated clubs: {updated}")
        print(f"Missing google_place_id after: {after}")
    else:
        print("Dry-run: no DB changes written")
        print(f"Accepted updates available: {len(accepted)}")
    print(f"Rejected/unresolved for manual review: {payload['rejected_or_unresolved_count']}")
    print(f"Excluded non-eligible rows: {payload['excluded_count']}")
    print(f"Google Places calls made: {quota.calls_made} of {quota.limit}")
    if args.json:
        print(f"Audit JSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
