"""Conservative, fair, and cached venue-coordinate enrichment.

The public Nominatim service permits regular jobs at four requests/minute.
One transaction advisory lock serializes all workers, while persisted attempts
both cache misses and prevent low-ID failures from monopolizing later batches.
"""

from __future__ import annotations

import math
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.database.connection import get_connection
from laughtrack.utilities.domain.club.timezone_lookup import parse_city_state_from_address

_DEFAULT_LIMIT = 30
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_USER_AGENT = "LaughTrack scraper geocoder (contact: admin@laughtrack.com)"
NOMINATIM_RATE_LIMIT_SECONDS = 15.0
_GEOCODE_LOCK_ID = 4046001


@dataclass(frozen=True)
class ClubCoordinateCandidate:
    id: int
    name: str
    address: str
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocode_attempt_count: int = 0


@dataclass(frozen=True)
class ClubGeocodingResult:
    attempted: int = 0
    resolved: int = 0
    unresolved: int = 0
    failed: int = 0
    retried: int = 0
    skipped: int = 0


class GeocodingProviderBlocked(RuntimeError):
    """The provider denied access or its quota; stop requests across runs."""


_CLUB_COORDINATE_SELECT_COLUMNS = (
    "id",
    "name",
    "address",
    "city",
    "state",
    "zip_code",
    "country",
    "latitude",
    "longitude",
    "geocode_attempt_count",
)


def _candidate_from_row(row) -> ClubCoordinateCandidate:
    values = dict(row) if hasattr(row, "keys") else dict(zip(_CLUB_COORDINATE_SELECT_COLUMNS, row))
    return ClubCoordinateCandidate(**values)


def _normalized(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def _street(value: str | None) -> str:
    words = re.findall(r"[a-z0-9]+", (value or "").casefold())
    aliases = {
        "street": "st",
        "road": "rd",
        "avenue": "ave",
        "boulevard": "blvd",
        "drive": "dr",
        "lane": "ln",
        "highway": "hwy",
        "court": "ct",
        "north": "n",
        "south": "s",
        "east": "e",
        "west": "w",
        "northeast": "ne",
        "northwest": "nw",
        "southeast": "se",
        "southwest": "sw",
    }
    return " ".join(aliases.get(word, word) for word in words)


def _country(club: ClubCoordinateCandidate) -> Optional[str]:
    aliases = {
        "us": "us",
        "usa": "us",
        "unitedstates": "us",
        "unitedstatesofamerica": "us",
        "ca": "ca",
        "canada": "ca",
        "uk": "gb",
        "gb": "gb",
        "unitedkingdom": "gb",
        "au": "au",
        "australia": "au",
        "nz": "nz",
        "newzealand": "nz",
        "ie": "ie",
        "ireland": "ie",
    }
    explicit = _normalized(club.country)
    suffix = _normalized((club.address or "").split(",")[-1])
    # CA is a US state and a country code; postal syntax disambiguates it.
    if suffix == "ca" and not re.fullmatch(r"[A-Z]\d[A-Z]\s?\d[A-Z]\d", club.zip_code or "", re.I):
        suffix = ""
    if explicit:
        country = aliases.get(explicit)
        if suffix in aliases and aliases[suffix] != country:
            return None
        return country
    if suffix in aliases:
        return aliases[suffix]
    # A parsed US state and five-digit ZIP establish country context even
    # when the source stores its ZIP separately from the full street address.
    _, state = parse_city_state_from_address(club.address)
    if state and re.fullmatch(r"\d{5}(?:-\d{4})?", club.zip_code or ""):
        return "us"
    return None


def _query_text(club: ClubCoordinateCandidate) -> str:
    parts = [club.address.strip()] if club.address else []
    for value in (club.city, club.state, club.zip_code, club.country):
        if value and not re.search(
            r"(?<![A-Za-z0-9])" + re.escape(value.strip()) + r"(?![A-Za-z0-9])", ", ".join(parts), re.I
        ):
            parts.append(value.strip())
    return ", ".join(parts)


def _valid_coordinates(coords) -> bool:
    try:
        lat, lon = coords
        return (
            math.isfinite(float(lat))
            and math.isfinite(float(lon))
            and -90 <= float(lat) <= 90
            and -180 <= float(lon) <= 180
        )
    except (TypeError, ValueError):
        return False


def _address_matches(club: ClubCoordinateCandidate, address: dict) -> bool:
    country = _country(club)
    if not country or address.get("country_code", "").lower() != country:
        return False
    postcode = _normalized(club.zip_code)
    if not postcode or postcode != _normalized(address.get("postcode")):
        return False
    # Require an actual house and road; a postal centroid or same-name POI is
    # never evidence for a venue's position.
    first = (club.address or "").split(",")[0].strip()
    match = re.fullmatch(r"(\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?)\s+(.+)", first)
    if not match or _normalized(match[1]) != _normalized(address.get("house_number")):
        return False
    if _street(match[2]) != _street(address.get("road")):
        return False
    parsed_city, parsed_state = parse_city_state_from_address(club.address) if country == "us" else (None, None)
    expected_cities = [club.city, parsed_city if parsed_state else None]
    for expected_city in filter(None, expected_cities):
        cities = [address.get(key) for key in ("city", "town", "village", "municipality", "borough")]
        if _normalized(expected_city) not in {_normalized(city) for city in cities if city}:
            return False
    for expected_state in filter(None, (club.state, parsed_state)):
        regions = [address.get("state"), address.get("state_code")]
        regions.extend(str(v).split("-")[-1] for key, v in address.items() if key.startswith("ISO3166-2"))
        if _normalized(expected_state) not in {_normalized(region) for region in regions if region}:
            return False
    return True


def _lookup_with_nominatim(club: ClubCoordinateCandidate) -> Optional[tuple[float, float]]:
    # Insufficient source identity is unresolved, not a reason to search a name.
    if not _country(club) or not club.zip_code or not re.match(r"^\d+\w*(?:-\d+\w*)?\s+", club.address or ""):
        return None
    import requests

    response = requests.get(
        os.environ.get("NOMINATIM_SEARCH_URL", _NOMINATIM_URL),
        params={"q": _query_text(club), "format": "jsonv2", "limit": 2, "addressdetails": 1},
        headers={"User-Agent": _NOMINATIM_USER_AGENT},
        timeout=10,
    )
    if response.status_code in (403, 429):
        raise GeocodingProviderBlocked(f"Nominatim returned HTTP {response.status_code}")
    response.raise_for_status()
    payload = response.json()
    matches = set()
    for item in payload:
        address = item.get("address")
        coords = (item.get("lat"), item.get("lon"))
        if isinstance(address, dict) and _valid_coordinates(coords) and _address_matches(club, address):
            matches.add((float(coords[0]), float(coords[1])))
    return next(iter(matches)) if len(matches) == 1 else None


def resolve_club_coordinates(club: ClubCoordinateCandidate) -> Optional[tuple[float, float]]:
    """Return only an unambiguous street-address match, never a ZIP centroid."""
    return _lookup_with_nominatim(club)


def _as_datetime(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _select_candidates(cur, limit: int, now: datetime) -> list[ClubCoordinateCandidate]:
    cur.execute(
        f"""
        SELECT {', '.join('c.' + column for column in _CLUB_COORDINATE_SELECT_COLUMNS)}
        FROM clubs c
        WHERE (c.latitude IS NULL OR c.longitude IS NULL)
          AND c.visible = TRUE AND c.status = 'active'
          AND c.club_type IN ('club', 'venue')
          AND (c.geocode_attempted_at IS NULL OR c.geocode_attempted_at <=
               CASE WHEN c.geocode_outcome IN ('failed', 'provider_blocked') THEN %s ELSE %s END)
        ORDER BY c.geocode_attempted_at ASC NULLS FIRST,
                 EXISTS(SELECT 1 FROM shows s WHERE s.club_id = c.id AND s.date > %s) DESC,
                 c.id
        LIMIT %s
        """,
        (now - timedelta(days=1), now - timedelta(days=7), now, limit),
    )
    return [_candidate_from_row(row) for row in cur.fetchall()]


def preview_missing_clubs(*, limit: int = _DEFAULT_LIMIT) -> list[ClubCoordinateCandidate]:
    """Read-only candidate preview: no provider requests or attempt writes."""
    if limit <= 0:
        return []
    with get_connection() as conn:
        with conn.cursor() as cur:
            return _select_candidates(cur, limit, datetime.now(timezone.utc))


def geocode_missing_clubs(
    *,
    limit: int = _DEFAULT_LIMIT,
    resolver: Callable[[ClubCoordinateCandidate], Optional[tuple[float, float]]] = resolve_club_coordinates,
    sleep: Callable[[float], None] = time.sleep,
) -> ClubGeocodingResult:
    """Fair bounded enrichment, serialized and cached across processes/runs."""
    if limit <= 0:
        return ClubGeocodingResult()
    attempted = resolved = unresolved = failed = retried = skipped = 0
    with get_connection(autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_xact_lock(%s)", (_GEOCODE_LOCK_ID,))
            if not cur.fetchone()[0]:
                return ClubGeocodingResult()
            now = datetime.now(timezone.utc)
            cur.execute("SELECT MAX(geocode_attempted_at) FROM clubs WHERE geocode_outcome = 'provider_blocked'")
            blocked_at = cur.fetchone()[0]
            if blocked_at and _as_datetime(blocked_at) > now - timedelta(days=1):
                return ClubGeocodingResult()
            cur.execute("SELECT MAX(geocode_attempted_at) FROM clubs")
            last_attempt = cur.fetchone()[0]
            rows = _select_candidates(cur, limit, now)
            for club in rows:
                if last_attempt:
                    remaining = (
                        NOMINATIM_RATE_LIMIT_SECONDS
                        - (datetime.now(timezone.utc) - _as_datetime(last_attempt)).total_seconds()
                    )
                    if remaining > 0:
                        sleep(remaining)
                attempted += 1
                retried += int(club.geocode_attempt_count > 0)
                coords = None
                outcome = "unresolved"
                blocked = False
                try:
                    coords = resolver(club)
                    if coords is not None and not _valid_coordinates(coords):
                        coords = None
                    if coords is not None:
                        # Never combine a new location with an incompatible known
                        # half of a coordinate pair, nor overwrite a known half.
                        if (club.latitude is not None and abs(club.latitude - float(coords[0])) > 0.00001) or (
                            club.longitude is not None and abs(club.longitude - float(coords[1])) > 0.00001
                        ):
                            coords = None
                        else:
                            outcome = "resolved"
                except GeocodingProviderBlocked as exc:
                    outcome, blocked = "provider_blocked", True
                    Logger.warn(f"Coordinate provider blocked for club_id={club.id}: {exc}")
                except Exception as exc:
                    outcome = "failed"
                    Logger.warn(f"Coordinate lookup failed for club_id={club.id}: {exc}")
                last_attempt = datetime.now(timezone.utc)
                lat, lon = coords if coords is not None else (None, None)
                # Snapshot guards also protect against a venue relocation or
                # concurrent ingestion filling either half during the request.
                cur.execute(
                    """UPDATE clubs SET latitude = COALESCE(latitude, %s), longitude = COALESCE(longitude, %s),
                           geocode_attempted_at = %s, geocode_attempt_count = geocode_attempt_count + 1,
                           geocode_outcome = %s
                       WHERE id = %s AND visible = TRUE AND status = 'active' AND club_type IN ('club', 'venue')
                         AND (latitude IS NULL OR longitude IS NULL)
                         AND name IS NOT DISTINCT FROM %s AND address IS NOT DISTINCT FROM %s
                         AND city IS NOT DISTINCT FROM %s AND state IS NOT DISTINCT FROM %s
                         AND zip_code IS NOT DISTINCT FROM %s AND country IS NOT DISTINCT FROM %s
                         AND latitude IS NOT DISTINCT FROM %s AND longitude IS NOT DISTINCT FROM %s""",
                    (
                        lat,
                        lon,
                        last_attempt,
                        outcome,
                        club.id,
                        club.name,
                        club.address,
                        club.city,
                        club.state,
                        club.zip_code,
                        club.country,
                        club.latitude,
                        club.longitude,
                    ),
                )
                if cur.rowcount:
                    resolved += int(outcome == "resolved")
                    unresolved += int(outcome == "unresolved")
                    failed += int(outcome in ("failed", "provider_blocked"))
                else:
                    skipped += 1
                if blocked:
                    break
        conn.commit()
    return ClubGeocodingResult(attempted, resolved, unresolved, failed, retried, skipped)
