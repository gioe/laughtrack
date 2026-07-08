#!/usr/bin/env python3
"""
Stamp House of Comedy Bloomington's numeric Tixr group id.

Background
----------
TASK-2403 added price backfill for the dedicated
``house_of_comedy_bloomington`` scraper when
``scraping_sources.metadata.tixr_group_id`` is configured. The venue-owned
calendar exposes event links under the public slug ``houseofcomedymn``, but
Tixr's group-events API requires the numeric group id.

Direct attempts against ``/api/groups/houseofcomedymn/events`` return HTTP 400,
and rendered Tixr pages are DataDome-blocked from automation. A user-captured
Chrome NetLog on 2026-05-23 showed the loaded group page requesting
``https://www.tixr.com/api/groups/2867``; probing
``/api/groups/2867/events`` through the scraper's Tixr transport returned live
House of Comedy MOA events with priced ``sales[].tiers[]``.

What this script does
---------------------
1. Validates the expected club and scraping_sources row shape.
2. Stamps ``scraping_sources.id=627`` metadata with ``tixr_group_id='2867'``.
3. Records TASK-2415 evidence in ``metadata.task_2415_tixr_group_id``.
4. Prints BEFORE/AFTER blocks for the ops audit trail.

Idempotent: only writes when the metadata differs. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_house_of_comedy_bloomington_tixr_group_id_2026_05_23.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_house_of_comedy_bloomington_tixr_group_id_2026_05_23.py
"""

import argparse
import json
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


_CLUB_ID = 655
_SOURCE_ID = 627
_TIXR_GROUP_ID = "2867"
_METADATA_KEY = "task_2415_tixr_group_id"
_EXPECTED_CLUB_NAME = "House of Comedy Bloomington"
_EXPECTED_WEBSITE = "https://moa.houseofcomedy.net"
_EXPECTED_SOURCE_URL = "https://moa.houseofcomedy.net/"
_EXPECTED_SCRAPER_KEY = "house_of_comedy_bloomington"


def _load_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is None:
        return {}
    return dict(raw)


def _shape_errors(club_row, source_row) -> list[str]:
    errors: list[str] = []
    if club_row is None:
        errors.append(f"clubs.id={_CLUB_ID} missing")
    else:
        club_id, name, website, visible, status = club_row
        if club_id != _CLUB_ID:
            errors.append(f"club id={club_id} (expected {_CLUB_ID})")
        if name != _EXPECTED_CLUB_NAME:
            errors.append(f"club name={name!r} (expected {_EXPECTED_CLUB_NAME!r})")
        if website != _EXPECTED_WEBSITE:
            errors.append(f"club website={website!r} (expected {_EXPECTED_WEBSITE!r})")
        if not visible:
            errors.append("club visible is false; expected a live visible venue")
        if status != "active":
            errors.append(f"club status={status!r} (expected active)")

    if source_row is None:
        errors.append(f"scraping_sources.id={_SOURCE_ID} missing")
    else:
        (
            source_id,
            club_id,
            platform,
            scraper_key,
            source_url,
            priority,
            enabled,
            metadata,
        ) = source_row
        if source_id != _SOURCE_ID:
            errors.append(f"source id={source_id} (expected {_SOURCE_ID})")
        if club_id != _CLUB_ID:
            errors.append(f"source club_id={club_id} (expected {_CLUB_ID})")
        if platform != "tixr":
            errors.append(f"source platform={platform!r} (expected tixr)")
        if scraper_key != _EXPECTED_SCRAPER_KEY:
            errors.append(f"source scraper_key={scraper_key!r} (expected {_EXPECTED_SCRAPER_KEY!r})")
        if source_url != _EXPECTED_SOURCE_URL:
            errors.append(f"source_url={source_url!r} (expected {_EXPECTED_SOURCE_URL!r})")
        if priority != 0:
            errors.append(f"priority={priority} (expected 0)")
        if not enabled:
            errors.append("source enabled is false; expected active scraper source")
        meta = _load_metadata(metadata)
        if meta.get("tixr_source_type") != "venue_public_card":
            errors.append(
                f"metadata.tixr_source_type={meta.get('tixr_source_type')!r} "
                "(expected venue_public_card)"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, website, visible, status
                FROM clubs
                WHERE id = %s
                """,
                (_CLUB_ID,),
            )
            club_row = cur.fetchone()

            cur.execute(
                """
                SELECT id, club_id, platform::text, scraper_key, source_url,
                       priority, enabled, metadata
                FROM scraping_sources
                WHERE id = %s
                """,
                (_SOURCE_ID,),
            )
            source_row = cur.fetchone()

        errors = _shape_errors(club_row, source_row)
        if errors:
            print("ABORT: shape mismatch - refusing to write:", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            return 1

        (
            source_id,
            club_id,
            platform,
            scraper_key,
            source_url,
            priority,
            enabled,
            metadata_raw,
        ) = source_row
        metadata = _load_metadata(metadata_raw)

        print("=== BEFORE ===")
        print(
            f"  club.id={club_row[0]} name={club_row[1]!r} "
            f"visible={club_row[3]} status={club_row[4]!r}"
        )
        print(
            f"  ss.id={source_id} club_id={club_id} platform={platform!r} "
            f"scraper_key={scraper_key!r} priority={priority} enabled={enabled} "
            f"source_url={source_url!r}"
        )
        print(f"  metadata.tixr_group_id={metadata.get('tixr_group_id')!r}")
        print(f"  metadata.{_METADATA_KEY}={metadata.get(_METADATA_KEY)!r}")

        new_metadata = dict(metadata)
        new_metadata["tixr_group_id"] = _TIXR_GROUP_ID
        new_metadata[_METADATA_KEY] = {
            "status": "resolved",
            "group_id": _TIXR_GROUP_ID,
            "slug": "houseofcomedymn",
            "resolved_at": "2026-05-23",
            "approach": (
                "Chrome NetLog capture of the user browser session showed "
                "the Tixr group page requesting /api/groups/2867; scraper "
                "transport probe of /api/groups/2867/events returned live "
                "House of Comedy MOA events with priced sales tiers."
            ),
            "verification": "make probe-tixr GROUP=2867 LIMIT=2",
        }

        if metadata == new_metadata:
            print("\nNo changes needed (idempotent re-run).")
            return 0

        print(
            f"\n{'PLAN ' if args.dry_run else 'WRITE'} ss={_SOURCE_ID}: "
            f"metadata.tixr_group_id={metadata.get('tixr_group_id')!r}->{_TIXR_GROUP_ID!r} + "
            f"metadata[{_METADATA_KEY}]"
        )
        if args.dry_run:
            print("\n--dry-run: 1 write planned (none applied).")
            return 0

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scraping_sources
                SET metadata = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, metadata
                """,
                (json.dumps(new_metadata), _SOURCE_ID),
            )
            updated = cur.fetchone()

        updated_metadata = _load_metadata(updated[1])
        print("\n=== AFTER ===")
        print(f"  ss.id={updated[0]} metadata.tixr_group_id={updated_metadata.get('tixr_group_id')!r}")
        print(
            f"  metadata[{_METADATA_KEY}].group_id="
            f"{updated_metadata[_METADATA_KEY]['group_id']!r}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
