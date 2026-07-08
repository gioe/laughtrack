#!/usr/bin/env python3
"""
TASK-2194: Delete the 12 historical false-positive comedian rows that were
amplified by show-name enrichment before TASK-2189 added them to
PLACEHOLDER_NAMES.

Background
----------
TASK-2189 traced inflated total_shows on rows like 'Drag', 'Sketch', 'Best of'
back to BATCH_GET_COMEDIANS_FROM_SHOW_NAME, which uses
``lower(show.name) LIKE '%' || lower(c.name) || '%'`` to attach comedians to
shows that mention them only as substrings. TASK-2189 plugged the source by
(a) extending PLACEHOLDER_NAMES so detect_false_positive() rejects new inserts
of these fragments at write time, and (b) extending the lineup query's
NOT IN list so the show-name matcher skips them. Existing rows and their
lineup_items were left in place pending this dedicated cleanup.

The 12 targeted names are the union of:
- The 11 fragments enumerated in TASK-2194's description
  (Drag, Sketch, ComedySportz, Best of, Alex, Blue, Down, LOVE, Columbus,
   JESSICA, Paranormal).
- 'Laughs' — added to PLACEHOLDER_NAMES in the same TASK-2189 commit and
  exhibiting the identical pollution pattern (53 lineup_items spread across
  multiple unrelated venues).

Audit on 2026-05-14 (read-only re-run of audit_false_positive_comedians.py
from the up-to-date branch) confirmed:
- 12 comedian rows match (one per fragment, case-insensitive exact name).
- ~488 lineup_items reference these rows across 71+ clubs.
- All 12 have parent_comedian_id IS NULL (no alias chains to preserve).
- None are in comedian_deny_list yet.

What this script does
---------------------
1. Looks up the 12 named fragments in `comedians` via case-insensitive exact
   match on lower(trim(name)).
2. Validates expected shape — refuses to write if any matched row has
   parent_comedian_id IS NOT NULL (those would be aliased to a real comedian
   and require manual review before deletion).
3. In one transaction:
   - Deletes lineup_items where comedian_id matches the resolved uuids.
   - Deletes the comedian rows.
   - Inserts each fragment name into comedian_deny_list with
     reason='task_2194_false_positive_fragment' and added_by='task_2194'
     (ON CONFLICT DO NOTHING — idempotent).
4. Prints BEFORE / AFTER counts for the ops audit trail.

Idempotent: on re-run, the comedians lookup returns 0 matches, deletes
nothing, and the deny-list inserts are no-ops via ON CONFLICT.

Substring safety: the lookup uses lower(trim(c.name)) = ANY(...) — exact
equality after lowercase + trim. Real comedians whose names *contain* one of
these fragments as a substring (e.g. 'Alex Borstein', 'Big Blue', 'LOVE Show
with Bobcat Goldthwait') are not matched and not affected.

Forensic discoverability: the comedian rows are removed (no metadata column
on comedians to annotate), so the audit trail lives in
(a) this script's git commit message ([TASK-2194]),
(b) the comedian_deny_list rows that carry reason='task_2194_*' and
    added_by='task_2194'.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/disposition_false_positive_comedian_fragments_2026_05_14.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/disposition_false_positive_comedian_fragments_2026_05_14.py
"""

import argparse
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from psycopg2.extras import execute_values

from laughtrack.adapters.db import get_transaction

# Lowercase exact-match targets. Order is preserved for readable output but
# the SQL match is set-based.
_TARGET_NAMES: tuple[str, ...] = (
    "alex",
    "best of",
    "blue",
    "columbus",
    "comedysportz",
    "down",
    "drag",
    "jessica",
    "laughs",
    "love",
    "paranormal",
    "sketch",
)

_DENY_REASON = "task_2194_false_positive_fragment"
_DENY_ADDED_BY = "task_2194"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete 12 historical false-positive comedian rows (TASK-2194).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the matched rows and intended writes without modifying the DB.",
    )
    args = parser.parse_args()

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.uuid,
                    c.name,
                    c.total_shows,
                    c.parent_comedian_id,
                    (
                        SELECT COUNT(*) FROM lineup_items li
                        WHERE li.comedian_id = c.uuid
                    ) AS lineup_count
                FROM comedians c
                WHERE lower(trim(c.name)) = ANY(%s)
                ORDER BY lower(trim(c.name)), c.name
                """,
                (list(_TARGET_NAMES),),
            )
            matched = cur.fetchall()

        # Shape validation: any aliased rows (parent_comedian_id IS NOT NULL)
        # require manual review — refuse to write.
        problems: list[str] = []
        for uuid, name, total_shows, parent_id, lineup_count in matched:
            if parent_id is not None:
                problems.append(
                    f"  uuid={uuid} name={name!r} has parent_comedian_id={parent_id} "
                    f"(aliased — refusing to delete without manual review)"
                )

        if problems:
            print("ABORT: shape mismatch — refusing to write:", file=sys.stderr)
            for p in problems:
                print(p, file=sys.stderr)
            return 1

        print("=" * 72)
        print(f"TASK-2194 disposition: false-positive comedian fragment cleanup")
        print("=" * 72)
        print()
        print(f"Targeted lowercase names ({len(_TARGET_NAMES)}):")
        print(f"  {', '.join(_TARGET_NAMES)}")
        print()
        print("=== BEFORE ===")
        if not matched:
            print("  (no comedians matched — nothing to delete; running deny-list backfill only.)")
        else:
            print(f"  {len(matched)} comedian row(s) matched:")
            for uuid, name, total_shows, _parent, lineup_count in matched:
                print(
                    f"    uuid={uuid} name={name!r} "
                    f"total_shows={total_shows} lineup_items={lineup_count}"
                )
            total_lineup = sum(r[4] for r in matched)
            print(f"  Total lineup_items to delete: {total_lineup}")

        cur_uuids = [r[0] for r in matched]
        cur_names = [r[1] for r in matched]

        # Pre-fetch deny-list state so we can show the AFTER delta accurately.
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name FROM comedian_deny_list WHERE lower(name) = ANY(%s)",
                (list(_TARGET_NAMES),),
            )
            already_denied = {r[0] for r in cur.fetchall()}

        print()
        print(f"  comedian_deny_list rows already present for these names: "
              f"{len(already_denied)}")
        if already_denied:
            for n in sorted(already_denied):
                print(f"    {n!r}")

        if args.dry_run:
            print()
            print("--dry-run: no DB write performed.")
            print("Re-run without --dry-run to execute the cleanup.")
            return 0

        deleted_lineup = 0
        deleted_comedians = 0
        if cur_uuids:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM lineup_items WHERE comedian_id = ANY(%s)",
                    (cur_uuids,),
                )
                deleted_lineup = cur.rowcount
                cur.execute(
                    "DELETE FROM comedians WHERE uuid = ANY(%s)",
                    (cur_uuids,),
                )
                deleted_comedians = cur.rowcount

        # Deny-list backfill: write the canonical lowercase form so future
        # lookups (which compare on lower(c.name)) match deterministically.
        # Use the matched names when available so capitalization mirrors what
        # was historically in the comedians table; otherwise fall back to the
        # canonical lowercase target.
        names_to_deny = cur_names if cur_names else list(_TARGET_NAMES)
        deny_rows = [(n, _DENY_REASON, _DENY_ADDED_BY) for n in names_to_deny]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO comedian_deny_list (name, reason, added_by)
                VALUES %s
                ON CONFLICT (name) DO NOTHING
                RETURNING name
                """,
                deny_rows,
            )
            newly_denied = [r[0] for r in cur.fetchall()]

        print()
        print("=== AFTER ===")
        print(f"  Deleted lineup_items: {deleted_lineup}")
        print(f"  Deleted comedians:    {deleted_comedians}")
        print(f"  Newly added to comedian_deny_list: {len(newly_denied)}")
        if newly_denied:
            for n in sorted(newly_denied):
                print(f"    {n!r}")

        # Verification probe inside the same transaction so we see the
        # post-write state before commit.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT lower(trim(c.name)), COUNT(*)
                FROM comedians c
                WHERE lower(trim(c.name)) = ANY(%s)
                GROUP BY 1
                """,
                (list(_TARGET_NAMES),),
            )
            remaining = cur.fetchall()
        if remaining:
            print()
            print("WARNING: post-delete probe still shows matched rows:", file=sys.stderr)
            for lname, cnt in remaining:
                print(f"  {lname!r}: {cnt}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
