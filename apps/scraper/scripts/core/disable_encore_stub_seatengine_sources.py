#!/usr/bin/env python3
"""
Disable the 6 dormant SeatEngine scraping_sources that scrape the
'Encore Comedy - <state>' stub clubs (id 639-644) at
https://encorecomedyshows.com/home/.

Background
----------
TASK-1924 audit (2026-05-04):
  - Encore Comedy (production_company id=4) migrated booking from SeatEngine to
    Eventbrite. Their `production_companies` row has scraping_url pointing at
    the new organizer feed (https://www.eventbrite.com/o/encore-comedy/72313162423/)
    which routes via the TASK-1891 synthetic-proxy path starting on the
    2026-05-05 nightly.
  - The 6 SeatEngine sources below were created when encorecomedyshows.com was
    the live booking surface. Direct probe of services.seatengine.com/api/v1
    (via `make seatengine-check ID=<external_id>`) confirms all 6 venues now
    return 0 upcoming shows. encorecomedyshows.com itself returns a domain
    parking page.
  - Net effect of leaving them enabled: 6 wasted SeatEngine API calls every
    nightly + risk of false-positive show resurrection if the integration ever
    re-populates with stale data. Disabling does not affect existing show rows
    on stub clubs; the 3 past shows on club 639 stay until natural age-out.
  - TASK-1917 dry-run confirmed 0 name collisions between the new pc=4
    Eventbrite per-venue clubs (55 clubs) and these 6 stubs, so disabling here
    cannot strand future Encore Comedy events under stub clubs by mistake.

Idempotent: only flips rows where enabled=true. Safe to re-run.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/disable_encore_stub_seatengine_sources.py
    cd apps/scraper && make run-script SCRIPT=scripts/core/disable_encore_stub_seatengine_sources.py ARGS='--dry-run'
"""

import argparse
import os
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

# (source_id, expected_club_id, expected_external_id)
_TARGETS: list[tuple[int, int, str]] = [
    (375, 639, "644"),  # Encore Comedy - Virginia
    (83,  640, "645"),  # Encore Comedy - Maryland
    (385, 641, "646"),  # Encore Comedy - North Carolina
    (363, 642, "647"),  # Encore Comedy - Kentucky
    (113, 643, "648"),  # Encore Comedy - DC
    (596, 644, "649"),  # Encore Comedy - Pennsylvania
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    target_ids = [t[0] for t in _TARGETS]

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, club_id, platform, scraper_key, external_id, source_url, enabled
                FROM scraping_sources WHERE id = ANY(%s) ORDER BY id
                """,
                (target_ids,),
            )
            rows = cur.fetchall()

        # Validate shape: all 6 must exist, platform=seatengine, source_url matches.
        by_id = {r[0]: r for r in rows}
        missing = [sid for sid in target_ids if sid not in by_id]
        if missing:
            print(f"ABORT: missing scraping_sources rows: {missing}", file=sys.stderr)
            return 1

        mismatches: list[str] = []
        for src_id, exp_club, exp_ext in _TARGETS:
            row = by_id[src_id]
            _, club_id, platform, scraper_key, external_id, source_url, _ = row
            if club_id != exp_club:
                mismatches.append(f"id={src_id}: club_id={club_id} (expected {exp_club})")
            if platform != "seatengine" or scraper_key != "seatengine":
                mismatches.append(
                    f"id={src_id}: platform/scraper_key={platform}/{scraper_key} "
                    f"(expected seatengine/seatengine)"
                )
            if external_id != exp_ext:
                mismatches.append(f"id={src_id}: external_id={external_id} (expected {exp_ext})")
            if "encorecomedyshows.com" not in (source_url or ""):
                mismatches.append(f"id={src_id}: source_url={source_url!r} (expected encorecomedyshows.com)")
        if mismatches:
            print("ABORT: shape mismatch — refusing to write:", file=sys.stderr)
            for m in mismatches:
                print(f"  {m}", file=sys.stderr)
            return 1

        print("=== BEFORE ===")
        for src_id, _, _ in _TARGETS:
            r = by_id[src_id]
            print(f"  id={r[0]} club_id={r[1]} external_id={r[4]} enabled={r[6]}")

        already_disabled = [sid for sid in target_ids if not by_id[sid][6]]
        to_update = [sid for sid in target_ids if by_id[sid][6]]
        print(f"\nalready disabled: {already_disabled}")
        print(f"will disable:     {to_update}")

        if not to_update:
            print("\nNo changes needed (idempotent re-run).")
            return 0

        if args.dry_run:
            print("\n--dry-run: no DB write performed.")
            return 0

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scraping_sources
                SET enabled = false, updated_at = NOW()
                WHERE id = ANY(%s) AND enabled = true
                RETURNING id, enabled, updated_at
                """,
                (to_update,),
            )
            updated = cur.fetchall()

        print("\n=== AFTER ===")
        for r in updated:
            print(f"  id={r[0]} enabled={r[1]} updated_at={r[2]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
