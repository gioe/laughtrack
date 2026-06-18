#!/usr/bin/env python3
"""
Dedup the duplicate club rows surfaced by the TASK-2945 google_place_id audit.

Background
----------
TASK-2945 nulled the misattributed google_place_id on non-canonical clubs that
shared a place_id, but left the duplicate club ROWS in place. This script removes
the duplication so each venue is listed once.

Two kinds of duplicate were found:

1. Junk / bulk-import rows — 0 shows, only a DISABLED ``tour_dates`` placeholder
   source. Safe to hide outright (nothing to reconcile):
       3003  "Stardome"                              (canonical 633)
       3044  "US Main Room, Hollywood Improv Interested" (canonical 3045)
       3046  "US Hollywood Casino Joliet Interested"  (canonical 2926)
       3047  "US Hollywood Casino Joliet"             (canonical 2926)
   2951 "713 Music Hall May 17 '26 ..." is already hidden (no-op here).

2. Bombs Away (same physical venue, 4579 Hamilton Ave, Cincinnati) — two clubs
   scraping two DIFFERENT eventbrite organizers at one venue:
       2290  "Bombs Away! Comedy at the Comet" (canonical, organizer 295891220)
       2291  "Bombs Away Comedy"               (GIT GUD open mic, organizer 296125770)
   The scraper selects ONE source per club (Club.primary_scraping_source), so the
   two organizers cannot live on one club without losing a scrape. Per the
   operator decision on TASK-2954 we consolidate to one club: move 2291's shows
   onto 2290 (no show loss at merge time), DISABLE 2291's eventbrite source so it
   cannot re-scrape the hidden club, and hide 2291. The eventbrite stale-show
   reconciler is organizer-scoped (TASK-2861), so 2290's own organizer scrape will
   not delete the moved rows.

Safety
------
Dry-run by default; pass --apply to write. Every statement is guarded so a
re-run is a no-op (idempotent): show moves filter on the source club_id, the
source-disable filters on enabled, and hides filter on visible=true.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/dedup_collision_clubs_2026_06_17.py
    make run-script SCRIPT=scripts/core/dedup_collision_clubs_2026_06_17.py ARGS='--apply'
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

# Junk / bulk-import duplicate club rows (0 shows, disabled placeholder source).
JUNK_CLUB_IDS = [3003, 3044, 3046, 3047]

# Bombs Away merge: distinct organizer at the same venue -> consolidate onto 2290.
BOMBS_AWAY_CANONICAL = 2290
BOMBS_AWAY_DUP = 2291
BOMBS_AWAY_DUP_SOURCE_ID = 1290  # 2291's eventbrite source (organizer 296125770)


def _scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dedup TASK-2945 collision club rows (dry-run by default)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the dedup. Without this flag the script previews and rolls back.",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    with get_transaction() as conn:
        with conn.cursor() as cur:
            # ---- BEFORE state ---------------------------------------------
            dup_shows = _scalar(
                cur, "SELECT COUNT(*) FROM shows WHERE club_id = %s", (BOMBS_AWAY_DUP,)
            )
            canon_shows = _scalar(
                cur, "SELECT COUNT(*) FROM shows WHERE club_id = %s", (BOMBS_AWAY_CANONICAL,)
            )
            dup_source_enabled = _scalar(
                cur,
                "SELECT enabled FROM scraping_sources WHERE id = %s AND club_id = %s",
                (BOMBS_AWAY_DUP_SOURCE_ID, BOMBS_AWAY_DUP),
            )
            cur.execute(
                "SELECT id, name, visible FROM clubs WHERE id = ANY(%s) ORDER BY id",
                (JUNK_CLUB_IDS + [BOMBS_AWAY_DUP, BOMBS_AWAY_CANONICAL],),
            )
            club_rows = cur.fetchall()

            print("BEFORE")
            for cid, name, visible in club_rows:
                print(f"  club {cid} visible={visible} {name!r}")
            print(
                f"  Bombs Away: dup {BOMBS_AWAY_DUP} has {dup_shows} shows, "
                f"canonical {BOMBS_AWAY_CANONICAL} has {canon_shows} shows; "
                f"dup source {BOMBS_AWAY_DUP_SOURCE_ID} enabled={dup_source_enabled}"
            )

            print("\nPLAN")
            print(
                f"  move {dup_shows} show(s) {BOMBS_AWAY_DUP} -> {BOMBS_AWAY_CANONICAL}; "
                f"disable source {BOMBS_AWAY_DUP_SOURCE_ID}; hide club {BOMBS_AWAY_DUP}"
            )
            print(f"  hide junk clubs {JUNK_CLUB_IDS} (already-hidden rows are no-ops)")

            if dry_run:
                print("\nDRY RUN: no changes written (pass --apply to write)")
                conn.rollback()
                return 0

            # ---- 1) Bombs Away: move shows 2291 -> 2290 (no show loss) -----
            cur.execute(
                "UPDATE shows SET club_id = %s WHERE club_id = %s",
                (BOMBS_AWAY_CANONICAL, BOMBS_AWAY_DUP),
            )
            moved = cur.rowcount

            # ---- 2) Disable 2291's eventbrite source ----------------------
            cur.execute(
                "UPDATE scraping_sources SET enabled = false WHERE id = %s AND club_id = %s",
                (BOMBS_AWAY_DUP_SOURCE_ID, BOMBS_AWAY_DUP),
            )
            source_disabled = cur.rowcount

            # ---- 3) Hide 2291 + the junk rows -----------------------------
            cur.execute(
                "UPDATE clubs SET visible = false WHERE id = ANY(%s) AND visible = true",
                ([BOMBS_AWAY_DUP] + JUNK_CLUB_IDS,),
            )
            hidden = cur.rowcount

            # ---- POST verification (criterion 9511) -----------------------
            still_visible_dups = _scalar(
                cur,
                "SELECT COUNT(*) FROM clubs WHERE id = ANY(%s) AND visible = true",
                ([BOMBS_AWAY_DUP] + JUNK_CLUB_IDS,),
            )
            remaining_on_dup = _scalar(
                cur, "SELECT COUNT(*) FROM shows WHERE club_id = %s", (BOMBS_AWAY_DUP,)
            )
            if still_visible_dups or remaining_on_dup:
                print(
                    f"Post-check failed: {still_visible_dups} dup club(s) still visible, "
                    f"{remaining_on_dup} show(s) still on {BOMBS_AWAY_DUP}"
                )
                conn.rollback()
                return 3

    print(
        f"\nMoved {moved} show(s) to {BOMBS_AWAY_CANONICAL}, "
        f"disabled {source_disabled} source(s), hid {hidden} club row(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
