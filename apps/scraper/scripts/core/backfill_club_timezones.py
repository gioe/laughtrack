#!/usr/bin/env python3
"""Backfill ``clubs.timezone`` for every visible club still missing one.

Runs a waterfall over each visible club where ``timezone IS NULL`` and resolves
an IANA timezone from the cheapest available signal first:

  1. Consistent state/address evidence in an unambiguous timezone region
  2. ``--geocode`` + the club's own Google place ID → unambiguous Place Details
  3. otherwise: unresolved (logged); name-only search never establishes identity

Step 2 also opportunistically fills ``clubs.state``/``address``/
``latitude``/``longitude`` when those
columns are currently NULL. Every write is NULL-guarded, so the script is safe
to re-run. ``--geocode`` is OFF by default so the nightly run stays cheap
(state/address only) and never touches the Places API quota.

Usage:
    python -m scripts.core.backfill_club_timezones
    python -m scripts.core.backfill_club_timezones --dry-run
    python -m scripts.core.backfill_club_timezones --limit 50
    python -m scripts.core.backfill_club_timezones --geocode
    python -m scripts.core.backfill_club_timezones --geocode --club-ids 12 34
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.core.clients.google.places import GooglePlacesClient, PlaceDetails
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.domain.club.timezone_lookup import (
    timezone_from_evidence,
)

# Resolution sources, used both as the dict keys in the run summary and as the
# value persisted in logs so each club's resolution path is auditable.
SOURCE_STATE = "state"
SOURCE_ADDRESS = "address"
SOURCE_PLACEID_GEOCODE = "placeid_geocode"
SOURCE_NAME_GEOCODE = "name_geocode"
SOURCE_UNRESOLVED = "unresolved"

_GET_CLUBS_SQL = """
    SELECT id, name, state, address, google_place_id, website, country
    FROM clubs
    WHERE visible = TRUE
      AND timezone IS NULL
      {extra_filter}
    ORDER BY id
"""

# NULL-guarded timezone write — only sets timezone when it is still NULL, so a
# concurrent writer (or a re-run) can never clobber a value set elsewhere.
_UPDATE_TIMEZONE_SQL = """
    UPDATE clubs
    SET timezone = %s
    WHERE id = %s AND timezone IS NULL
"""

# Opportunistic identity enrichment from an AUTHORITATIVE geocode — the club's
# OWN google_place_id (SOURCE_PLACEID_GEOCODE) — each column guarded so only
# currently-NULL columns are filled (manual edits / prior values win). NEVER
# applied to a SOURCE_NAME_GEOCODE result: a name text-search is a heuristic
# match that can land on an unrelated famous venue (TASK-2933: club 620 'Comedy
# Shows Near Me' matched Comedy Cellar's place_id + 117 MacDougal St address),
# so writing its address/coords/place_id back corrupts club identity.
_UPDATE_GEOCODE_FIELDS_SQL = """
    UPDATE clubs
    SET state     = COALESCE(state, %s),
        address   = COALESCE(NULLIF(address, ''), %s),
        latitude  = COALESCE(latitude, %s),
        longitude = COALESCE(longitude, %s)
    WHERE id = %s
"""


@dataclass
class ClubRow:
    """A visible club row with a NULL timezone awaiting resolution."""

    id: int
    name: Optional[str]
    state: Optional[str]
    address: Optional[str]
    google_place_id: Optional[str]
    website: Optional[str]
    country: Optional[str] = None


@dataclass
class Resolution:
    """Outcome of resolving one club's timezone.

    ``details`` carries the Place Details payload when the resolution came from
    a geocode step, so the caller can opportunistically backfill state/address/
    coordinates from the club's stored place ID.
    """

    source: str
    timezone: Optional[str]
    details: Optional[PlaceDetails] = None
    resolved_place_id: Optional[str] = None


def derive_timezone(
    row: ClubRow,
    client: Optional[GooglePlacesClient],
    geocode: bool,
) -> Resolution:
    """Resolve one club's timezone via the cheapest-first waterfall.

    Pure aside from the optional Places API calls made through ``client`` when
    ``geocode`` is True; returns a :class:`Resolution` describing which source
    won (or ``SOURCE_UNRESOLVED``) without performing any DB writes.
    """
    source, tz = timezone_from_evidence(row.state, row.address, row.country)
    if tz:
        return Resolution(source=source, timezone=tz)

    if geocode and client is not None and row.google_place_id:
        details = client.fetch_place_details(row.google_place_id)
        if details:
            # The stored place ID identifies this venue. Name-only search does
            # not, and must never invent its timezone from an unrelated match.
            _, tz = timezone_from_evidence(details.state_code, details.formatted_address, row.country)
            # A stored place ID can itself be wrong. Require both stored
            # region fields to agree with the details before accepting it.
            _, state_agreement = timezone_from_evidence(row.state, details.formatted_address, row.country)
            _, address_agreement = timezone_from_evidence(details.state_code, row.address, row.country)
            if tz and state_agreement == tz and address_agreement == tz:
                return Resolution(source=SOURCE_PLACEID_GEOCODE, timezone=tz, details=details)

    return Resolution(source=SOURCE_UNRESOLVED, timezone=None)


def _load_target_clubs(club_ids: Optional[List[int]], limit: Optional[int]) -> List[ClubRow]:
    filters: List[str] = []
    params: List = []
    if club_ids:
        filters.append("AND id = ANY(%s::int[])")
        params.append(club_ids)
    sql = _GET_CLUBS_SQL.format(extra_filter="\n      ".join(filters))
    if limit:
        sql += f"\n    LIMIT {int(limit)}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            rows = cur.fetchall()
    return [
        ClubRow(
            id=r[0],
            name=r[1],
            state=r[2],
            address=r[3],
            google_place_id=r[4],
            website=r[5],
            country=r[6],
        )
        for r in rows
    ]


def _persist(row: ClubRow, resolution: Resolution) -> None:
    """Write the resolved timezone (NULL-guarded) plus source-gated geocode fields.

    Identity columns (address/lat/lng and any resolved place_id) are backfilled
    ONLY for ``SOURCE_PLACEID_GEOCODE`` — that resolution used the club's own
    ``google_place_id``, so its Place Details authoritatively describe this club.
    Name-search results are rejected even if passed directly by an old caller.
    """
    if resolution.source not in {SOURCE_STATE, SOURCE_ADDRESS, SOURCE_PLACEID_GEOCODE} or not resolution.timezone:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_UPDATE_TIMEZONE_SQL, (resolution.timezone, row.id))
            details = resolution.details
            if details is not None and resolution.source == SOURCE_PLACEID_GEOCODE:
                cur.execute(
                    _UPDATE_GEOCODE_FIELDS_SQL,
                    (
                        details.state_code,
                        details.formatted_address,
                        details.lat,
                        details.lng,
                        row.id,
                    ),
                )
        conn.commit()


def run(
    *,
    club_ids: Optional[List[int]],
    limit: Optional[int],
    geocode: bool,
    dry_run: bool,
) -> Dict[str, int]:
    """Execute the backfill and return per-source resolution counts."""
    targets = _load_target_clubs(club_ids, limit)
    Logger.info(
        f"[tz-backfill] {len(targets)} visible clubs with NULL timezone " f"(geocode={geocode}, dry_run={dry_run})"
    )

    summary: Dict[str, int] = {
        SOURCE_STATE: 0,
        SOURCE_ADDRESS: 0,
        SOURCE_PLACEID_GEOCODE: 0,
        SOURCE_NAME_GEOCODE: 0,
        SOURCE_UNRESOLVED: 0,
        "written": 0,
    }

    client: Optional[GooglePlacesClient] = None
    if geocode:
        client = GooglePlacesClient()
        if not client.is_configured:
            Logger.warn("[tz-backfill] --geocode set but GOOGLE_PLACES_API_KEY missing — geocode steps will no-op")

    for row in targets:
        resolution = derive_timezone(row, client, geocode)
        summary[resolution.source] += 1

        if resolution.source == SOURCE_UNRESOLVED:
            Logger.warn(
                f"[tz-backfill] unresolved: club {row.id} '{row.name}' "
                f"(state={row.state!r}, address={row.address!r})"
            )
            continue

        # When a geocode step won, surface the resolved address so name-search
        # matches can be audited (a wrong venue match yields a wrong timezone).
        geocode_note = ""
        if resolution.details is not None:
            geocode_note = f" [resolved: {resolution.details.formatted_address!r}]"

        if dry_run:
            Logger.info(
                f"[tz-backfill] would set club {row.id} '{row.name}' -> "
                f"{resolution.timezone} (via {resolution.source}){geocode_note}"
            )
            continue

        _persist(row, resolution)
        summary["written"] += 1
        Logger.info(
            f"[tz-backfill] set club {row.id} '{row.name}' -> "
            f"{resolution.timezone} (via {resolution.source}){geocode_note}"
        )

    Logger.info(
        "[tz-backfill] done — "
        f"state={summary[SOURCE_STATE]}, address={summary[SOURCE_ADDRESS]}, "
        f"placeid_geocode={summary[SOURCE_PLACEID_GEOCODE]}, "
        f"name_geocode={summary[SOURCE_NAME_GEOCODE]}, "
        f"unresolved={summary[SOURCE_UNRESOLVED]}, written={summary['written']}"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill clubs.timezone for visible clubs missing one, via a "
            "state -> address -> (optional) Google Places waterfall."
        ),
    )
    parser.add_argument(
        "--club-ids",
        nargs="+",
        type=int,
        default=None,
        help="Limit run to specific club IDs (otherwise every NULL-tz visible club is eligible).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N clubs (useful for smoke-testing).",
    )
    parser.add_argument(
        "--geocode",
        action="store_true",
        help="Enable Google Places lookup for stored place IDs only. Off by default.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve + log what would change, but do not write to the database.",
    )

    args = parser.parse_args()

    try:
        run(
            club_ids=args.club_ids,
            limit=args.limit,
            geocode=args.geocode,
            dry_run=args.dry_run,
        )
    except KeyboardInterrupt:
        Logger.info("[tz-backfill] cancelled by user")
        sys.exit(130)
    except Exception as exc:
        Logger.error(f"[tz-backfill] failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
