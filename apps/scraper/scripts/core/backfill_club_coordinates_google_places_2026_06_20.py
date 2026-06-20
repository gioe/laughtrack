#!/usr/bin/env python3
"""Backfill missing club coordinates from Google Places (TASK-3032).

Dry-run by default. The script only writes coordinates for active, visible
physical venue rows (``club_type='club'``). Producer, festival, hidden, closed,
and secret-location rows are excluded and reported so non-venue source targets
do not receive coordinates by accident.
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

_TASK_ID = 3032
_DESCRIPTION_MARKER = "TASK-3032 coordinate backfill:"
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
_DETAILS_FIELD_MASK = "formattedAddress,location,addressComponents,websiteUri,primaryType,displayName"
_WORD_RE = re.compile(r"[a-z0-9]+")
_STATE_RE = re.compile(r"\b[A-Z]{2}\b")
_WEAK_NAME_TOKENS = {
    "a",
    "an",
    "and",
    "at",
    "club",
    "comedy",
    "event",
    "events",
    "improv",
    "live",
    "lounge",
    "near",
    "night",
    "room",
    "shows",
    "the",
    "theater",
    "theatre",
    "us",
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
    latitude: float | None
    longitude: float | None
    shows_count: int
    future_shows_count: int
    scraping_sources_count: int
    enabled_sources_count: int
    production_company_mappings: int


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write accepted coordinates to the DB.")
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
    filters = ["c.latitude IS NULL OR c.longitude IS NULL"]
    params: list[Any] = []
    if club_ids:
        filters.append("c.id = ANY(%s::int[])")
        params.append(club_ids)

    cur.execute(
        f"""
        SELECT
            c.id, c.name, c.address, c.city, c.state, c.zip_code, c.country, c.website,
            c.status, c.visible, c.club_type, c.google_place_id, c.latitude, c.longitude,
            COUNT(DISTINCT s.id) AS shows_count,
            COUNT(DISTINCT s.id) FILTER (WHERE s.date > NOW()) AS future_shows_count,
            COUNT(DISTINCT ss.id) AS scraping_sources_count,
            COUNT(DISTINCT ss.id) FILTER (WHERE ss.enabled = TRUE) AS enabled_sources_count,
            COUNT(DISTINCT pcv.production_company_id) AS production_company_mappings
        FROM clubs c
        LEFT JOIN shows s ON s.club_id = c.id
        LEFT JOIN scraping_sources ss ON ss.club_id = c.id
        LEFT JOIN production_company_venues pcv ON pcv.club_id = c.id
        WHERE {" AND ".join(f"({f})" for f in filters)}
        GROUP BY c.id
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
            latitude=float(row["latitude"]) if row["latitude"] is not None else None,
            longitude=float(row["longitude"]) if row["longitude"] is not None else None,
            shows_count=int(row["shows_count"] or 0),
            future_shows_count=int(row["future_shows_count"] or 0),
            scraping_sources_count=int(row["scraping_sources_count"] or 0),
            enabled_sources_count=int(row["enabled_sources_count"] or 0),
            production_company_mappings=int(row["production_company_mappings"] or 0),
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


def _validate(row: ClubRow, result: PlaceResult) -> tuple[bool, str]:
    if result.lat is None or result.lng is None:
        return False, "missing coordinates"
    if not result.formatted_address:
        return False, "missing formatted address"

    expected_state = _normalize_state(row.state)
    actual_state = _normalize_state(result.state_code)
    if expected_state and actual_state and expected_state != actual_state:
        return False, f"state mismatch: expected {expected_state}, got {actual_state}"

    if result.source == "existing_google_place_id":
        return True, "accepted existing google_place_id details"

    expected_zip = (row.zip_code or "").strip()
    zip_matches = bool(expected_zip and expected_zip[:5].isdigit() and expected_zip[:5] in result.formatted_address)
    if expected_zip and expected_zip[:5].isdigit() and not zip_matches:
        return False, f"zip mismatch or absent: expected {expected_zip[:5]}"

    row_tokens = _tokens(row.name)
    result_tokens = _tokens(result.display_name)
    overlap = row_tokens & result_tokens
    row_street_number = _street_number(row.address)
    result_street_number = _street_number(result.formatted_address)
    street_number_matches = bool(
        row_street_number and result_street_number and row_street_number == result_street_number
    )
    if row_tokens and len(overlap) < min(2, len(row_tokens)):
        if not (overlap and (zip_matches or street_number_matches)):
            return False, f"weak name match: {sorted(overlap)}"

    return True, "accepted text search match with name/state/address context"


def _street_number(address: str | None) -> str | None:
    if not address:
        return None
    match = re.search(r"\b\d{1,6}\b", address)
    return match.group(0) if match else None


def _fetch_details(quota: PlacesQuota, place_id: str) -> tuple[PlaceResult | None, str | None]:
    if not quota.reserve():
        return None, "skipped: Google Places request quota exhausted"
    try:
        response = requests.get(
            f"{_API_BASE}/places/{place_id}",
            headers={"X-Goog-Api-Key": quota.api_key, "X-Goog-FieldMask": _DETAILS_FIELD_MASK},
            timeout=quota.timeout_s,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        return None, f"place details failed: {exc}"
    if not isinstance(data, dict):
        return None, "place details returned non-object JSON"
    return _place_result_from_payload("existing_google_place_id", place_id, data), None


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

    query: str | None = None
    if row.google_place_id:
        result, error = _fetch_details(quota, row.google_place_id)
    else:
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
    return (
        f"{_DESCRIPTION_MARKER} coordinates resolved from Google Places {result.source} "
        f"for place_id={result.place_id}; {row.reason}"
    )


def _write_accepted(cur: RealDictCursor, accepted: list[AuditRow]) -> int:
    values = []
    for row in accepted:
        result = row.result
        assert result is not None
        values.append((row.club.id, result.place_id, result.lat, result.lng, _description_note(row)))
    if not values:
        return 0

    cur.execute("""
        CREATE TEMP TABLE task_3032_coordinate_backfill (
            club_id integer PRIMARY KEY,
            google_place_id text NOT NULL,
            latitude double precision NOT NULL,
            longitude double precision NOT NULL,
            note text NOT NULL
        ) ON COMMIT DROP
        """)
    execute_values(
        cur,
        """
        INSERT INTO task_3032_coordinate_backfill
            (club_id, google_place_id, latitude, longitude, note)
        VALUES %s
        """,
        values,
    )
    cur.execute(
        """
        UPDATE clubs c
        SET google_place_id = COALESCE(c.google_place_id, b.google_place_id),
            latitude = b.latitude,
            longitude = b.longitude,
            description = CASE
                WHEN COALESCE(c.description, '') LIKE %s THEN c.description
                WHEN COALESCE(c.description, '') = '' THEN b.note
                ELSE c.description || E'\n\n' || b.note
            END
        FROM task_3032_coordinate_backfill b
        WHERE c.id = b.club_id
          AND (c.latitude IS NULL OR c.longitude IS NULL)
        """,
        (f"%{_DESCRIPTION_MARKER}%",),
    )
    return int(cur.rowcount or 0)


def _missing_count(cur: RealDictCursor) -> int:
    cur.execute("SELECT COUNT(*) AS count FROM clubs WHERE latitude IS NULL OR longitude IS NULL")
    return int(cur.fetchone()["count"])


def _audit_payload(rows: list[AuditRow], before: int, after: int | None, calls_made: int) -> dict[str, Any]:
    accepted = [row for row in rows if row.accepted]
    rejected = [row for row in rows if row.eligible and not row.accepted]
    excluded = [row for row in rows if not row.eligible]
    return {
        "task_id": _TASK_ID,
        "missing_coordinates_before": before,
        "missing_coordinates_after": after,
        "google_places_calls_made": calls_made,
        "accepted_count": len(accepted),
        "rejected_or_unresolved_count": len(rejected),
        "excluded_count": len(excluded),
        "accepted": [
            {
                "club_id": row.club.id,
                "name": row.club.name,
                "source": row.result.source if row.result else None,
                "place_id": row.result.place_id if row.result else None,
                "lat": row.result.lat if row.result else None,
                "lng": row.result.lng if row.result else None,
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

    print(f"Missing coordinates before: {before}")
    if args.apply:
        print(f"Updated clubs: {updated}")
        print(f"Missing coordinates after: {after}")
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
