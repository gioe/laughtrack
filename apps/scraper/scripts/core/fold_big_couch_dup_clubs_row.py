#!/usr/bin/env python3
"""
Fold the duplicate 'Big Couch' clubs row (id=2287) created by the 2026-05-05
Eventbrite organizer-mode nightly into the existing club 654
'Big Couch New Orleans'.

Background
----------
TASK-1916 audit found the Eventbrite organizer feed for organizer.id
29220617465 returns 134 events split across 25 distinct venue.id values
under two name spellings: 90 events with venue.name='Big Couch' and 44 with
venue.name='Big Couch New Orleans'. All 25 venue.ids resolve to the same
physical New Orleans, LA address, but the (name, city, state) dedupe key in
EventbriteScraper._venue_dedupe_key collapses them into 2 upsert groups,
so under organizer mode the nightly fires UPSERT_CLUB_BY_EVENTBRITE_VENUE
twice. The first call (group='Big Couch') inserts a new clubs row because
ON CONFLICT (name) finds no match against the existing 'Big Couch
New Orleans' row.

TASK-1919 chose leave-as-is rather than rename/repoint because both
alternatives were rejected (rename only inverts the split; venue-mode
repoint silently drops 100+ events). Filed this task as the post-nightly
manual fold (criterion 6314 equivalent).

Observed post-nightly state (2026-05-05 ~10:30 UTC)
---------------------------------------------------
Today's nightly produced clubs.id=2287 ('Big Couch') and
scraping_sources.id=1286 (eventbrite, external_id='295549203'), but the
new row carries 0 shows — all 131 matched organizer-feed events still
sit on club 654. The fold target is therefore trivial: no show rows
need re-pointing. We just need to hide row 2287 so it doesn't appear
in user search and rely on UPSERT_CLUB_BY_EVENTBRITE_VENUE's
ON CONFLICT (name) path to reuse the hidden row on subsequent nightlies
(no NEW dup ever created).

What this script does
---------------------
1. Validates the expected shape of clubs.id=2287 and scraping_sources.id=1286.
2. Verifies clubs.id=2287 has 0 shows (defensive — refuses to write
   otherwise, since constraint shows_club_id_date_room_key would block
   a naive UPDATE-set-club_id=654 on conflict and we'd want a human
   to disambiguate).
3. Sets clubs.id=2287 visible=FALSE.
4. Annotates scraping_sources.id=1286 metadata with the cleanup context.

Idempotent: only flips clubs.visible when currently TRUE, only writes
metadata if the cleanup key is absent. Safe to re-run.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/fold_big_couch_dup_clubs_row.py
    cd apps/scraper && make run-script SCRIPT=scripts/core/fold_big_couch_dup_clubs_row.py ARGS='--dry-run'
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

from laughtrack.adapters.db import get_connection

_DUP_CLUB_ID = 2287
_DUP_CLUB_NAME = "Big Couch"
_SURVIVING_CLUB_ID = 654
_DUP_SOURCE_ID = 1286
_DUP_SOURCE_EXTERNAL_ID = "295549203"
_METADATA_KEY = "task_1925_hidden_dup"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, city, state, visible
                FROM clubs WHERE id = ANY(%s) ORDER BY id
                """,
                ([_DUP_CLUB_ID, _SURVIVING_CLUB_ID],),
            )
            club_rows = {r[0]: r for r in cur.fetchall()}

            cur.execute(
                """
                SELECT id, club_id, platform, external_id, enabled, metadata
                FROM scraping_sources WHERE id = %s
                """,
                (_DUP_SOURCE_ID,),
            )
            src_row = cur.fetchone()

            cur.execute(
                "SELECT COUNT(*) FROM shows WHERE club_id = %s",
                (_DUP_CLUB_ID,),
            )
            dup_show_count = cur.fetchone()[0]

        # Shape validation
        problems: list[str] = []
        if _DUP_CLUB_ID not in club_rows:
            problems.append(f"clubs.id={_DUP_CLUB_ID} missing")
        else:
            _, name, city, state, _ = club_rows[_DUP_CLUB_ID]
            if name != _DUP_CLUB_NAME:
                problems.append(f"clubs.id={_DUP_CLUB_ID} name={name!r} (expected {_DUP_CLUB_NAME!r})")
            if (city, state) != ("New Orleans", "LA"):
                problems.append(
                    f"clubs.id={_DUP_CLUB_ID} (city,state)=({city!r},{state!r}) "
                    f"(expected ('New Orleans','LA'))"
                )

        if _SURVIVING_CLUB_ID not in club_rows:
            problems.append(f"clubs.id={_SURVIVING_CLUB_ID} missing")

        if src_row is None:
            problems.append(f"scraping_sources.id={_DUP_SOURCE_ID} missing")
        else:
            _, src_club, platform, ext_id, _, _ = src_row
            if src_club != _DUP_CLUB_ID:
                problems.append(
                    f"scraping_sources.id={_DUP_SOURCE_ID} club_id={src_club} "
                    f"(expected {_DUP_CLUB_ID})"
                )
            if platform != "eventbrite":
                problems.append(
                    f"scraping_sources.id={_DUP_SOURCE_ID} platform={platform!r} (expected 'eventbrite')"
                )
            if ext_id != _DUP_SOURCE_EXTERNAL_ID:
                problems.append(
                    f"scraping_sources.id={_DUP_SOURCE_ID} external_id={ext_id!r} "
                    f"(expected {_DUP_SOURCE_EXTERNAL_ID!r})"
                )

        if dup_show_count != 0:
            problems.append(
                f"clubs.id={_DUP_CLUB_ID} has {dup_show_count} shows — refusing to hide. "
                f"Re-point shows to {_SURVIVING_CLUB_ID} first (and resolve any "
                f"(club_id, date, room) constraint collisions by hand)."
            )

        if problems:
            print("ABORT: shape mismatch — refusing to write:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1

        dup_id, dup_name, dup_city, dup_state, dup_visible = club_rows[_DUP_CLUB_ID]
        src_id, src_club_id, src_platform, src_ext_id, src_enabled, src_metadata = src_row
        if isinstance(src_metadata, str):
            src_metadata = json.loads(src_metadata)
        elif src_metadata is None:
            src_metadata = {}

        print("=== BEFORE ===")
        print(
            f"  clubs.id={dup_id} name={dup_name!r} ({dup_city!r}, {dup_state!r}) "
            f"visible={dup_visible} shows={dup_show_count}"
        )
        print(
            f"  scraping_sources.id={src_id} club_id={src_club_id} platform={src_platform!r} "
            f"external_id={src_ext_id!r} enabled={src_enabled} metadata={src_metadata!r}"
        )

        will_hide_club = bool(dup_visible)
        will_annotate_source = _METADATA_KEY not in src_metadata

        print()
        print(f"will set clubs.id={_DUP_CLUB_ID} visible=FALSE: {will_hide_club}")
        print(f"will annotate scraping_sources.id={_DUP_SOURCE_ID} metadata: {will_annotate_source}")

        if not (will_hide_club or will_annotate_source):
            print("\nNo changes needed (idempotent re-run).")
            return 0

        if args.dry_run:
            print("\n--dry-run: no DB write performed.")
            return 0

        with conn.cursor() as cur:
            if will_hide_club:
                cur.execute(
                    "UPDATE clubs SET visible = FALSE WHERE id = %s AND visible = TRUE "
                    "RETURNING id, visible",
                    (_DUP_CLUB_ID,),
                )
                club_after = cur.fetchone()
            else:
                club_after = (_DUP_CLUB_ID, dup_visible)

            if will_annotate_source:
                new_metadata = dict(src_metadata)
                new_metadata[_METADATA_KEY] = {
                    "hidden_club_id": _DUP_CLUB_ID,
                    "surviving_club_id": _SURVIVING_CLUB_ID,
                    "rationale": (
                        "Duplicate clubs row created by Eventbrite organizer-mode "
                        "(name, city, state) dedupe — hidden so it doesn't surface in "
                        "user search. Source kept enabled so subsequent nightlies hit "
                        "ON CONFLICT (name) on the hidden row instead of creating a new dup."
                    ),
                }
                cur.execute(
                    "UPDATE scraping_sources SET metadata = %s, updated_at = NOW() "
                    "WHERE id = %s RETURNING id, metadata",
                    (json.dumps(new_metadata), _DUP_SOURCE_ID),
                )
                src_after = cur.fetchone()
            else:
                src_after = (_DUP_SOURCE_ID, src_metadata)

        conn.commit()

        print("\n=== AFTER ===")
        print(f"  clubs.id={club_after[0]} visible={club_after[1]}")
        print(f"  scraping_sources.id={src_after[0]} metadata={src_after[1]!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
