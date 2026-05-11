"""Geocode clubs that are missing latitude/longitude.

Address-level via OpenStreetMap Nominatim (free, 1 req/sec under their ToS),
falling back to zip-centroid via the existing pgeocode helper when address
lookup fails. Idempotent — re-running only touches rows still missing coords.

Usage:
    # Dry-run: print what would change, no DB writes
    python scripts/core/backfill_club_coordinates.py

    # Apply: UPDATE clubs.latitude/longitude for resolved rows
    python scripts/core/backfill_club_coordinates.py --apply

    # Limit to N clubs (useful for smoke-testing)
    python scripts/core/backfill_club_coordinates.py --limit 5 --apply
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure local 'src' takes precedence over any installed laughtrack package.
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from laughtrack.infrastructure.database.connection import create_connection  # noqa: E402
from laughtrack.core.services.notification.geo import ZipCodeDistance  # noqa: E402
from laughtrack.utilities.domain.club.coordinates import (  # noqa: E402
    NOMINATIM_RATE_LIMIT_SECONDS,
    geocode_address,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write UPDATEs to DB")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N clubs")
    args = parser.parse_args()

    zip_geo = ZipCodeDistance()

    with create_connection(autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, address, zip_code
                FROM clubs
                WHERE status = 'active'
                  AND (latitude IS NULL OR longitude IS NULL)
                ORDER BY id
                """
            )
            rows = cur.fetchall()

        if args.limit is not None:
            rows = rows[: args.limit]

        print(f"Found {len(rows)} active clubs missing coordinates")
        resolved_address = 0
        resolved_zip = 0
        unresolved = 0
        last_call_at = 0.0

        for club_id, name, address, zip_code in rows:
            coords = None

            if address:
                # Rate-limit: at most one Nominatim call per second.
                elapsed = time.monotonic() - last_call_at
                if elapsed < NOMINATIM_RATE_LIMIT_SECONDS:
                    time.sleep(NOMINATIM_RATE_LIMIT_SECONDS - elapsed)
                coords = geocode_address(address)
                last_call_at = time.monotonic()
                if coords:
                    resolved_address += 1

            if coords is None and zip_code:
                coords = zip_geo.get_coords(zip_code)
                if coords:
                    resolved_zip += 1

            if coords is None:
                unresolved += 1
                print(f"  [miss] club {club_id} {name!r} address={address!r} zip={zip_code!r}")
                continue

            lat, lon = coords
            print(f"  [ok]   club {club_id} {name!r} -> ({lat:.5f}, {lon:.5f})")

            if args.apply:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE clubs SET latitude = %s, longitude = %s WHERE id = %s",
                        (lat, lon, club_id),
                    )

        if args.apply:
            conn.commit()
            print("Committed UPDATEs.")
        else:
            conn.rollback()
            print("Dry-run — no DB changes. Re-run with --apply to write.")

        print(
            f"Summary: address={resolved_address} zip={resolved_zip} "
            f"unresolved={unresolved} total={len(rows)}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
