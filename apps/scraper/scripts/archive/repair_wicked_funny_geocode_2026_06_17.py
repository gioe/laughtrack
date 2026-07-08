#!/usr/bin/env python3
"""
Re-geocode Wicked Funny Danvers (636) and Salisbury (637) to their own venues.

Background
----------
TASK-2945 found that clubs 636 (Wicked Funny Comedy Club Danvers) and 637
(Wicked Funny Comedy Club Salisbury) — two distinct venues — had both been
mis-geocoded by the old name_geocode path to a single shared place_id
(ChIJ4furWdMH44kRyGkqh2wqtvM) at 946 Osgood St, North Andover, MA, which is
neither town. TASK-2945 nulled google_place_id/address/latitude/longitude on
both (keeping state=MA + timezone), so they now have no geocoding.

Each runs its comedy shows at a distinct host restaurant, visible in the show
titles ("... at Magia" for Danvers, "... at The Hungry Traveler" for Salisbury):

    636 Danvers   -> Magia, Danvers MA
    637 Salisbury -> The Hungry Traveler, Salisbury MA

What this script does
---------------------
For each club it resolves the host venue via Google Places (find_place_id ->
fetch_place_details — the same authoritative place_id-geocode path the fixed
backfill_club_timezones now uses) and writes the resolved
google_place_id/address/latitude/longitude/city/state back onto the club.

Safety / validation (refuses to write a club on any failure)
- resolved place_id must NOT be the North Andover collision id,
- resolved state must be MA,
- the expected town must appear in the formatted address,
- the two clubs must resolve to *different* place_ids (no re-collision).

Dry-run by default; pass --apply to write. Idempotent: re-running resolves the
same places and rewrites the same values.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/repair_wicked_funny_geocode_2026_06_17.py
    make run-script SCRIPT=scripts/core/repair_wicked_funny_geocode_2026_06_17.py ARGS='--apply'
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction
from laughtrack.core.clients.google.places import GooglePlacesClient

# The mis-attributed place_id TASK-2945 stripped off both clubs.
NORTH_ANDOVER_PLACE_ID = "ChIJ4furWdMH44kRyGkqh2wqtvM"


@dataclass(frozen=True)
class Target:
    club_id: int
    query: str
    expected_town: str
    expected_state: str


TARGETS: list[Target] = [
    Target(club_id=636, query="Magia restaurant Danvers MA", expected_town="Danvers", expected_state="MA"),
    Target(
        club_id=637,
        query="The Hungry Traveler restaurant Salisbury MA",
        expected_town="Salisbury",
        expected_state="MA",
    ),
]


_UPDATE_SQL = """
    UPDATE clubs
    SET google_place_id = %s,
        address = %s,
        latitude = %s,
        longitude = %s,
        city = COALESCE(%s, city),
        state = COALESCE(%s, state)
    WHERE id = %s
"""


@dataclass
class Resolved:
    target: Target
    place_id: str | None
    address: str | None
    state_code: str | None
    city: str | None
    lat: float | None
    lng: float | None
    problems: list[str]


def _resolve(client: GooglePlacesClient, target: Target) -> Resolved:
    problems: list[str] = []
    place_id = client.find_place_id(target.query)
    if not place_id:
        problems.append(f"no place_id resolved for query {target.query!r}")
        return Resolved(target, None, None, None, None, None, None, problems)

    if place_id == NORTH_ANDOVER_PLACE_ID:
        problems.append(f"resolved to the North Andover collision place_id {place_id}")

    details = client.fetch_place_details(place_id)
    if details is None:
        problems.append(f"no place details for {place_id}")
        return Resolved(target, place_id, None, None, None, None, None, problems)

    addr = details.formatted_address
    if not addr:
        problems.append("no formatted address")
    elif target.expected_town.lower() not in addr.lower():
        problems.append(f"expected town {target.expected_town!r} not in address {addr!r}")

    if details.state_code != target.expected_state:
        problems.append(f"state {details.state_code!r} != expected {target.expected_state!r}")

    if details.lat is None or details.lng is None:
        problems.append("missing lat/lng")

    return Resolved(
        target=target,
        place_id=place_id,
        address=addr,
        state_code=details.state_code,
        city=details.city,
        lat=details.lat,
        lng=details.lng,
        problems=problems,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-geocode Wicked Funny clubs 636/637 (dry-run by default)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the resolved geocoding. Without this flag the script previews and rolls back.",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    client = GooglePlacesClient()
    if not client.is_configured:
        print("GOOGLE_PLACES_API_KEY is not set; cannot resolve places.")
        return 2

    resolved = [_resolve(client, t) for t in TARGETS]

    print("RESOLUTION")
    for r in resolved:
        print(f"  club {r.target.club_id} <- {r.target.query!r}")
        print(f"    place_id={r.place_id}")
        print(f"    address={r.address}")
        print(f"    city={r.city} state={r.state_code} lat={r.lat} lng={r.lng}")
        for p in r.problems:
            print(f"    PROBLEM: {p}")

    # Cross-check: the two clubs must not re-collide on one place_id.
    ids = [r.place_id for r in resolved if r.place_id]
    if len(ids) != len(set(ids)):
        for r in resolved:
            r.problems.append("two clubs resolved to the same place_id (would re-collide)")

    problems = [p for r in resolved for p in r.problems]
    if problems:
        print("\nRefusing to write — unresolved problems:")
        for p in problems:
            print(f"  - {p}")
        return 2

    if dry_run:
        print("\nDRY RUN: no changes written (pass --apply to write)")
        return 0

    with get_transaction() as conn:
        with conn.cursor() as cur:
            for r in resolved:
                cur.execute(
                    _UPDATE_SQL,
                    (r.place_id, r.address, r.lat, r.lng, r.city, r.state_code, r.target.club_id),
                )
                if cur.rowcount != 1:
                    print(f"Expected to update 1 row for club {r.target.club_id}; affected {cur.rowcount}")
                    conn.rollback()
                    return 3

    print(f"\nWrote geocoding for {len(resolved)} club(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
