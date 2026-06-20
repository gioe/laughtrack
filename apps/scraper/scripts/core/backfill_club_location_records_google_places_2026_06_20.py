#!/usr/bin/env python3
"""Resolve incomplete club location rows through Google Places.

TASK-3027 helper. Dry-run by default: loads clubs with blank or coarse address
values, resolves them with Google Places, prints an audit report, and can emit
idempotent SQL suitable for an ``apps/scraper/migrations`` data migration.
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
from typing import Any, Iterable, Optional

import requests

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_connection  # noqa: E402
from laughtrack.core.clients.google.places import GooglePlacesClient, PlaceDetails  # noqa: E402

SOURCE_PLACE_ID = "place_id"
SOURCE_TEXT_SEARCH = "text_search"

_PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_TEXT_SEARCH_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.websiteUri,"
    "places.primaryType"
)

_STATE_RE = re.compile(r"\b[A-Z]{2}\b")
_WORD_RE = re.compile(r"[a-z0-9]+")
_WEAK_NAME_TOKENS = {
    "a",
    "an",
    "and",
    "at",
    "club",
    "comedy",
    "event",
    "events",
    "near",
    "me",
    "room",
    "shows",
    "the",
    "us",
}


@dataclass(frozen=True)
class ClubCandidate:
    id: int
    name: str
    address: str
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    website: str
    visible: bool
    status: str
    club_type: str
    google_place_id: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    shows_count: int
    scraping_sources_count: int
    enabled_sources_count: int
    production_company_mappings: int
    favorites_count: int


@dataclass(frozen=True)
class PlaceResolution:
    source: str
    place_id: str
    display_name: Optional[str]
    formatted_address: Optional[str]
    city: Optional[str]
    state_code: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    website: Optional[str]
    primary_type: Optional[str]


@dataclass(frozen=True)
class Validation:
    accepted: bool
    reason: str


@dataclass(frozen=True)
class AuditRow:
    club: ClubCandidate
    query: Optional[str]
    resolution: Optional[PlaceResolution]
    validation: Validation


def is_incomplete_address(address: Optional[str]) -> bool:
    """Return True for blank, city/state-only, or partial street addresses."""
    value = (address or "").strip()
    if not value:
        return True
    if re.fullmatch(r"[A-Za-z .'-]+,\s*[A-Z]{2}", value):
        return True
    if "," not in value:
        return True
    return False


def build_search_query(row: ClubCandidate) -> str:
    """Build a Places text-search query from stable club identity fields."""
    parts = [row.name.strip()]
    if row.city:
        parts.append(row.city.strip())
    if row.state:
        parts.append(row.state.strip())
    if len(parts) == 1 and row.website:
        parts.append(row.website.strip())
    return " ".join(p for p in parts if p)


def _tokens(value: Optional[str]) -> set[str]:
    return {t for t in _WORD_RE.findall((value or "").lower()) if t not in _WEAK_NAME_TOKENS}


def _normalize_state(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip().upper()
    return value if re.fullmatch(r"[A-Z]{2}", value) else None


def validate_resolution(row: ClubCandidate, result: PlaceResolution) -> Validation:
    """Decide whether a Places result is strong enough to backfill identity."""
    if not result.formatted_address:
        return Validation(False, "missing formatted address")
    if result.lat is None or result.lng is None:
        return Validation(False, "missing coordinates")

    expected_state = _normalize_state(row.state)
    actual_state = _normalize_state(result.state_code)
    if expected_state and actual_state and expected_state != actual_state:
        return Validation(False, f"state mismatch: expected {expected_state}, got {actual_state}")

    if result.source == SOURCE_PLACE_ID:
        return Validation(True, "accepted from existing google_place_id")

    row_tokens = _tokens(row.name)
    result_tokens = _tokens(result.display_name)
    overlap = row_tokens & result_tokens
    has_location_context = bool(row.city or row.state)
    if not overlap and not has_location_context:
        return Validation(False, "weak name match and no location context")
    if row_tokens and len(overlap) < min(2, len(row_tokens)) and not expected_state:
        return Validation(False, "weak name match")

    return Validation(True, "accepted from text search with matching identity context")


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _candidate_from_row(row: tuple[Any, ...]) -> ClubCandidate:
    return ClubCandidate(
        id=row[0],
        name=row[1],
        address=row[2] or "",
        city=row[3],
        state=row[4],
        country=row[5],
        website=row[6] or "",
        visible=row[7],
        status=row[8],
        club_type=row[9],
        google_place_id=row[10],
        latitude=float(row[11]) if row[11] is not None else None,
        longitude=float(row[12]) if row[12] is not None else None,
        shows_count=int(row[13] or 0),
        scraping_sources_count=int(row[14] or 0),
        enabled_sources_count=int(row[15] or 0),
        production_company_mappings=int(row[16] or 0),
        favorites_count=int(row[17] or 0),
    )


def load_candidates(club_ids: Optional[list[int]] = None) -> list[ClubCandidate]:
    filters = [
        """
        (
            address IS NULL
            OR btrim(address) = ''
            OR (
                address IS NOT NULL
                AND btrim(address) <> ''
                AND (length(btrim(address)) < 6 OR btrim(address) !~ '[0-9]')
            )
        )
        """
    ]
    params: list[Any] = []
    if club_ids:
        filters.append("c.id = ANY(%s::int[])")
        params.append(club_ids)

    sql = f"""
        SELECT
            c.id, c.name, c.address, c.city, c.state, c.country, c.website,
            c.visible, c.status, c.club_type, c.google_place_id,
            c.latitude, c.longitude,
            COUNT(DISTINCT s.id) AS shows_count,
            COUNT(DISTINCT ss.id) AS scraping_sources_count,
            COUNT(DISTINCT ss_enabled.id) AS enabled_sources_count,
            COUNT(DISTINCT pcv.production_company_id) AS production_company_mappings,
            COUNT(DISTINCT fav.id) AS favorites_count
        FROM clubs c
        LEFT JOIN shows s ON s.club_id = c.id
        LEFT JOIN scraping_sources ss ON ss.club_id = c.id
        LEFT JOIN scraping_sources ss_enabled ON ss_enabled.club_id = c.id AND ss_enabled.enabled = TRUE
        LEFT JOIN production_company_venues pcv ON pcv.club_id = c.id
        LEFT JOIN favorite_clubs fav ON fav.club_id = c.id
        WHERE {" AND ".join(filters)}
        GROUP BY c.id
        ORDER BY c.id
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            return [_candidate_from_row(row) for row in cur.fetchall()]


def _resolution_from_details(source: str, place_id: str, details: PlaceDetails) -> PlaceResolution:
    return PlaceResolution(
        source=source,
        place_id=place_id,
        display_name=None,
        formatted_address=details.formatted_address,
        city=details.city,
        state_code=details.state_code,
        lat=details.lat,
        lng=details.lng,
        website=None,
        primary_type=None,
    )


def _parse_search_place(place: dict[str, Any]) -> Optional[PlaceResolution]:
    place_id = place.get("id")
    if not isinstance(place_id, str) or not place_id:
        return None
    display = place.get("displayName")
    display_name = display.get("text") if isinstance(display, dict) else None
    location = place.get("location")
    lat = location.get("latitude") if isinstance(location, dict) else None
    lng = location.get("longitude") if isinstance(location, dict) else None
    address = place.get("formattedAddress")
    return PlaceResolution(
        source=SOURCE_TEXT_SEARCH,
        place_id=place_id,
        display_name=display_name if isinstance(display_name, str) else None,
        formatted_address=address if isinstance(address, str) else None,
        city=None,
        state_code=_extract_state_from_address(address if isinstance(address, str) else None),
        lat=float(lat) if isinstance(lat, (int, float)) else None,
        lng=float(lng) if isinstance(lng, (int, float)) else None,
        website=place.get("websiteUri") if isinstance(place.get("websiteUri"), str) else None,
        primary_type=place.get("primaryType") if isinstance(place.get("primaryType"), str) else None,
    )


def _extract_state_from_address(address: Optional[str]) -> Optional[str]:
    if not address:
        return None
    matches = _STATE_RE.findall(address)
    return matches[-1] if matches else None


def text_search_top(query: str, *, delay_s: float = 0.15, timeout_s: float = 10.0) -> Optional[PlaceResolution]:
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if not api_key or not query.strip():
        return None
    if delay_s > 0:
        time.sleep(delay_s)
    resp = requests.post(
        _PLACES_SEARCH_URL,
        json={"textQuery": query, "pageSize": 1},
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": _TEXT_SEARCH_FIELD_MASK,
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    data = resp.json()
    places = data.get("places") if isinstance(data, dict) else None
    if not isinstance(places, list) or not places:
        return None
    top = places[0]
    return _parse_search_place(top) if isinstance(top, dict) else None


def resolve_candidate(client: GooglePlacesClient, row: ClubCandidate) -> AuditRow:
    query: Optional[str] = None
    resolution: Optional[PlaceResolution] = None
    if row.google_place_id:
        details = client.fetch_place_details(row.google_place_id)
        if details is not None:
            resolution = _resolution_from_details(SOURCE_PLACE_ID, row.google_place_id, details)
    else:
        query = build_search_query(row)
        resolution = text_search_top(query)

    validation = (
        validate_resolution(row, resolution)
        if resolution is not None
        else Validation(False, "no Google Places result")
    )
    return AuditRow(row, query, resolution, validation)


def generate_update_sql(rows: Iterable[AuditRow]) -> str:
    accepted = [row for row in rows if row.validation.accepted and row.resolution is not None]
    lines = [
        "-- TASK-3027: Google Places-backed club location backfill.",
        "-- Generated by scripts/core/backfill_club_location_records_google_places_2026_06_20.py.",
        "",
        "CREATE TEMP TABLE club_location_google_places_backfill (",
        "    club_id integer PRIMARY KEY,",
        "    place_id text NOT NULL,",
        "    address text NOT NULL,",
        "    city text,",
        "    state text,",
        "    latitude double precision,",
        "    longitude double precision,",
        "    source text NOT NULL,",
        "    rationale text NOT NULL",
        ") ON COMMIT DROP;",
        "",
    ]
    if accepted:
        lines.append(
            "INSERT INTO club_location_google_places_backfill "
            "(club_id, place_id, address, city, state, latitude, longitude, source, rationale)"
        )
        lines.append("VALUES")
        value_lines = []
        for row in accepted:
            res = row.resolution
            assert res is not None
            value_lines.append(
                "    ("
                + ", ".join(
                    [
                        sql_literal(row.club.id),
                        sql_literal(res.place_id),
                        sql_literal(res.formatted_address),
                        sql_literal(res.city),
                        sql_literal(res.state_code),
                        sql_literal(res.lat),
                        sql_literal(res.lng),
                        sql_literal(res.source),
                        sql_literal(row.validation.reason),
                    ]
                )
                + ")"
            )
        lines.append(",\n".join(value_lines) + ";")
    else:
        lines.append("-- No accepted Google Places backfills.")
    lines.extend(
        [
            "",
            "UPDATE clubs c",
            "SET google_place_id = b.place_id,",
            "    address = b.address,",
            "    city = COALESCE(b.city, c.city),",
            "    state = COALESCE(b.state, c.state),",
            "    latitude = COALESCE(b.latitude, c.latitude),",
            "    longitude = COALESCE(b.longitude, c.longitude),",
            "    country = COALESCE(c.country, 'US'),",
            "    description = concat_ws(",
            "        E'\\n\\n',",
            "        NULLIF(c.description, ''),",
            "        'Updated by TASK-3027 via Google Places ' || b.source || ': ' || b.rationale",
            "    )",
            "FROM club_location_google_places_backfill b",
            "WHERE c.id = b.club_id",
            "  AND (c.address IS NULL OR btrim(c.address) = '' OR c.address <> b.address);",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--club-ids", nargs="+", type=int, default=None)
    parser.add_argument("--json", type=Path, default=None, help="Write full audit JSON to this path.")
    parser.add_argument("--sql", type=Path, default=None, help="Write generated update SQL to this path.")
    args = parser.parse_args()

    client = GooglePlacesClient()
    if not client.is_configured:
        print("GOOGLE_PLACES_API_KEY is not set; cannot resolve places.", file=sys.stderr)
        return 2

    candidates = load_candidates(args.club_ids)
    audit_rows = [resolve_candidate(client, row) for row in candidates]

    accepted = [row for row in audit_rows if row.validation.accepted]
    rejected = [row for row in audit_rows if not row.validation.accepted]
    print(f"Resolved {len(audit_rows)} affected row(s): accepted={len(accepted)}, rejected={len(rejected)}")
    for row in rejected:
        print(f"REJECT {row.club.id} {row.club.name}: {row.validation.reason}")

    if args.json:
        args.json.write_text(
            json.dumps(
                [
                    {
                        "club": asdict(row.club),
                        "query": row.query,
                        "resolution": asdict(row.resolution) if row.resolution else None,
                        "validation": asdict(row.validation),
                    }
                    for row in audit_rows
                ],
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    sql = generate_update_sql(audit_rows)
    if args.sql:
        args.sql.write_text(sql, encoding="utf-8")
    else:
        print(sql)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
