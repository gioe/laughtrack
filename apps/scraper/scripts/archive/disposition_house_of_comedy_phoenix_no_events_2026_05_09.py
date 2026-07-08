#!/usr/bin/env python3
"""
Disable the upstream-empty House of Comedy Phoenix custom scraping source.

Background
----------
TASK-2102 investigated club 2355, Rick Bronson's House of Comedy Phoenix,
after the newly onboarded ``house_of_comedy_phoenix`` scraper found zero shows.

Direct probes through the scraper's own HTTP stack on 2026-05-09 confirmed:

* The public page still renders the ShowClix WordPress widget.
* The widget AJAX endpoint
  https://az.houseofcomedy.net/wp-admin/admin-ajax.php
  accepts ``action=get_comedy_shows`` with the expected month/year parameters.
* Every probed month in 2025, 2026, and 2027 returns only
  ``<p class="empty-response">No upcoming comedy shows found</p>`` with no
  links, no event cards, and no ShowClix event payload.

Disposition: disable the single custom scraping_sources row. No club hide is
performed because the public venue site is still live; this only stops a known
empty upstream feed from running nightly until the venue republishes inventory.

What this script does
---------------------
1. Validates the expected club and scraping_sources row shape.
2. Updates scraping_sources.id=1359 to ``enabled=false``.
3. Stamps ``metadata.task_2102_disposition`` with the evidence and rationale.
4. Prints BEFORE/AFTER blocks for the ops audit trail.

Idempotent: only writes when ``enabled`` is currently True OR the metadata key
is missing. Safe to re-run.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/disposition_house_of_comedy_phoenix_no_events_2026_05_09.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/disposition_house_of_comedy_phoenix_no_events_2026_05_09.py
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


_CLUB_ID = 2355
_SOURCE_ID = 1359
_METADATA_KEY = "task_2102_disposition"
_DISPOSITION_KIND = "upstream_empty_no_events"
_EXPECTED_SOURCE_URL = "https://az.houseofcomedy.net/upcoming-comedy-shows/"
_EXPECTED_AJAX_URL = "https://az.houseofcomedy.net/wp-admin/admin-ajax.php"


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
        club_id, name, visible, status = club_row
        if club_id != _CLUB_ID:
            errors.append(f"club id={club_id} (expected {_CLUB_ID})")
        if name != "Rick Bronson's House of Comedy Phoenix":
            errors.append(f"club name={name!r} (expected Rick Bronson's House of Comedy Phoenix)")
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
            metadata,
        ) = source_row
        if source_id != _SOURCE_ID:
            errors.append(f"source id={source_id} (expected {_SOURCE_ID})")
        if club_id != _CLUB_ID:
            errors.append(f"source club_id={club_id} (expected {_CLUB_ID})")
        if platform != "custom":
            errors.append(f"source platform={platform!r} (expected custom)")
        if scraper_key != "house_of_comedy_phoenix":
            errors.append(f"source scraper_key={scraper_key!r} (expected house_of_comedy_phoenix)")
        if source_url != _EXPECTED_SOURCE_URL:
            errors.append(f"source_url={source_url!r} (expected {_EXPECTED_SOURCE_URL})")
        if priority != 0:
            errors.append(f"priority={priority} (expected 0)")
        meta = _load_metadata(metadata)
        if meta.get("ajax_url") != _EXPECTED_AJAX_URL:
            errors.append(f"metadata.ajax_url={meta.get('ajax_url')!r} (expected {_EXPECTED_AJAX_URL})")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, visible, status
                FROM clubs
                WHERE id = %s
                """,
                (_CLUB_ID,),
            )
            club_row = cur.fetchone()

            cur.execute(
                """
                SELECT id, club_id, platform::text, scraper_key, source_url,
                       priority, metadata, enabled
                FROM scraping_sources
                WHERE id = %s
                """,
                (_SOURCE_ID,),
            )
            source_row_with_enabled = cur.fetchone()

        source_row = source_row_with_enabled[:7] if source_row_with_enabled else None
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
            metadata_raw,
            enabled,
        ) = source_row_with_enabled
        metadata = _load_metadata(metadata_raw)

        print("=== BEFORE ===")
        print(
            f"  club.id={club_row[0]} name={club_row[1]!r} "
            f"visible={club_row[2]} status={club_row[3]!r}"
        )
        print(
            f"  ss.id={source_id} club_id={club_id} platform={platform!r} "
            f"scraper_key={scraper_key!r} priority={priority} enabled={enabled} "
            f"source_url={source_url!r}"
        )

        needs_disable = bool(enabled)
        needs_meta = _METADATA_KEY not in metadata
        if not (needs_disable or needs_meta):
            print("\nNo changes needed (idempotent re-run).")
            return 0

        new_metadata = dict(metadata)
        new_metadata[_METADATA_KEY] = {
            "kind": _DISPOSITION_KIND,
            "rationale": (
                "House of Comedy Phoenix AJAX endpoint is reachable but returns "
                "the empty-response marker for every probed month across 2025, "
                "2026, and 2027. Disable the source to stop recurring zero-event "
                "nightly runs until the venue republishes ShowClix inventory."
            ),
            "source_url": _EXPECTED_SOURCE_URL,
            "ajax_url": _EXPECTED_AJAX_URL,
            "evidence_date": "2026-05-09",
            "probed_years": [2025, 2026, 2027],
            "empty_response": '<p class="empty-response">No upcoming comedy shows found</p>',
        }

        action = "PLAN " if args.dry_run else "WRITE"
        print(
            f"\n{action} ss={_SOURCE_ID}: enabled={enabled}->FALSE + "
            f"metadata[{_METADATA_KEY}]={_DISPOSITION_KIND!r}"
        )
        if args.dry_run:
            print("\n--dry-run: 1 write planned (none applied).")
            return 0

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scraping_sources
                SET enabled = FALSE,
                    metadata = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, enabled, metadata
                """,
                (json.dumps(new_metadata), _SOURCE_ID),
            )
            updated = cur.fetchone()

        print("\n=== AFTER ===")
        print(
            f"  ss.id={updated[0]} enabled={updated[1]} "
            f"metadata[{_METADATA_KEY}]={updated[2][_METADATA_KEY]['kind']!r}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
