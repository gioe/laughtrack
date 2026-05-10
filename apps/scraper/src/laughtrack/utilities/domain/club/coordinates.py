"""Incremental club coordinate enrichment."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.database.connection import get_connection

_DEFAULT_LIMIT = 30
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_USER_AGENT = "LaughTrack scraper geocoder (contact: admin@laughtrack.com)"


@dataclass(frozen=True)
class ClubCoordinateCandidate:
    id: int
    name: str
    address: str
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]


@dataclass(frozen=True)
class ClubGeocodingResult:
    attempted: int = 0
    resolved: int = 0
    unresolved: int = 0


def _candidate_from_row(row) -> ClubCoordinateCandidate:
    return ClubCoordinateCandidate(
        id=int(row["id"]),
        name=row.get("name", ""),
        address=row.get("address", ""),
        city=row.get("city"),
        state=row.get("state"),
        zip_code=row.get("zip_code"),
    )


def _query_text(club: ClubCoordinateCandidate) -> str:
    parts = [club.address, club.city, club.state, club.zip_code]
    return ", ".join(str(part).strip() for part in parts if str(part or "").strip())


def _valid_coord(value) -> bool:
    try:
        return not math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def _lookup_with_nominatim(club: ClubCoordinateCandidate) -> Optional[tuple[float, float]]:
    query = _query_text(club)
    if not query:
        return None

    import requests

    response = requests.get(
        _NOMINATIM_URL,
        params={"q": query, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": _NOMINATIM_USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload:
        return None
    first = payload[0]
    lat = first.get("lat")
    lon = first.get("lon")
    if not _valid_coord(lat) or not _valid_coord(lon):
        return None
    return float(lat), float(lon)


def _lookup_with_pgeocode(club: ClubCoordinateCandidate) -> Optional[tuple[float, float]]:
    zip_code = (club.zip_code or "").strip()[:5]
    if not zip_code:
        return None

    import pgeocode

    result = pgeocode.Nominatim("us").query_postal_code(zip_code)
    if result is None or not _valid_coord(getattr(result, "latitude", None)):
        return None
    lon = getattr(result, "longitude", None)
    if not _valid_coord(lon):
        return None
    return float(result.latitude), float(lon)


def resolve_club_coordinates(club: ClubCoordinateCandidate) -> Optional[tuple[float, float]]:
    """Resolve club coordinates using Nominatim first, then zip-code fallback."""
    try:
        coords = _lookup_with_nominatim(club)
    except Exception as exc:
        Logger.warn(f"Nominatim lookup failed for club_id={club.id} name={club.name!r}: {exc}")
        coords = None
    return coords or _lookup_with_pgeocode(club)


def geocode_missing_clubs(
    *,
    limit: int = _DEFAULT_LIMIT,
    resolver: Callable[[ClubCoordinateCandidate], Optional[tuple[float, float]]] = resolve_club_coordinates,
    sleep: Callable[[float], None] = time.sleep,
) -> ClubGeocodingResult:
    """Resolve coordinates for a bounded batch of clubs missing lat/lon."""
    if limit <= 0:
        return ClubGeocodingResult()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, address, city, state, zip_code
                FROM clubs
                WHERE latitude IS NULL OR longitude IS NULL
                ORDER BY id
                LIMIT %s
                """,
                (limit,),
            )
            rows: Iterable = list(cur.fetchall())

            attempted = 0
            resolved = 0
            unresolved = 0
            total_rows = len(rows)
            for index, row in enumerate(rows):
                attempted += 1
                club = _candidate_from_row(row)
                try:
                    coords = resolver(club)
                except Exception as exc:
                    Logger.warn(f"Club geocoding failed for club_id={club.id} name={club.name!r}: {exc}")
                    coords = None
                if coords is None:
                    unresolved += 1
                    continue

                lat, lon = coords
                cur.execute(
                    """
                    UPDATE clubs
                    SET latitude = %s, longitude = %s
                    WHERE id = %s
                      AND (latitude IS NULL OR longitude IS NULL)
                    """,
                    (lat, lon, club.id),
                )
                resolved += cur.rowcount or 0
                if index < total_rows - 1:
                    sleep(1.0)

    return ClubGeocodingResult(attempted=attempted, resolved=resolved, unresolved=unresolved)
