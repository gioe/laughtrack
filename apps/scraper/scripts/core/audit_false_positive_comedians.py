"""
TASK-605: Audit DB for false-positive comedian records.

Surfaces comedian records created from placeholder names (e.g. "TBA", "Special Guest")
that slipped through lineup extraction before TASK-603 added the deny-list filter.

Run:
    cd apps/scraper && .venv/bin/python scripts/core/audit_false_positive_comedians.py

Output columns:
    comedian_name   — the stored name
    lineup_count    — number of lineup_items rows pointing to this comedian
    sample_show_ids — up to 5 show IDs where the comedian appears (for targeted re-scraping)

Placeholder detection criteria (OR):
  1. Name matches a known placeholder string (case-insensitive): TBA, TBD, To Be Announced,
     Special Guest, Surprise Guest, Surprise Act, Mystery Guest, Comedy Show, Various Artists,
     Headliner, Featured Comedian, Local Comedian, Guest Comedian, Open Mic, Host, MC,
     Emcee, Opener, Headliner TBD, Lineup TBA, More TBA, Plus More, And More, And Special Guests
  2. Name contains a placeholder substring: "open mic", "open-mic"
  3. Name length < 4 characters (single-name tokens that are almost never real comedian names)

Structural detection criteria (OR):
  1. Name contains a pipe character (|)
  2. Name length > 60 characters
  3. Name contains a non-person keyword: revue, burlesque, variety, showcase, production,
     presents, festival, extravaganza, theatre, theater, entertainment

Usage after reviewing results:
    - Note which clubs have the most affected shows.
    - Once TASK-603 is deployed (false-positive filter live), queue those clubs for re-scraping
      so lineup_items are healed with real comedian records.

Flags:
    --delete            Show what would be deleted (dry-run). Requires --confirm to actually delete.
    --confirm           Combined with --delete: permanently removes identified comedian records
                        and their lineup_items rows.
    --csv <path>        Write all findings (placeholder + structural) to a CSV file with columns:
                        comedian_name, detection_type, lineup_count, all_show_ids,
                        club_name, club_id, affected_shows
    --merge             Show merge candidates — false positives whose name contains exactly one
                        real two-word comedian name as a substring. Dry-run unless --confirm
                        is also passed.
    --deny-list-add <name>    Insert a name directly into comedian_deny_list with added_by='manual'.
                              No-op if the name already exists.
    --deny-list-reason <txt>  Reason string stored alongside the name (default: 'manual_entry').
                              Only used with --deny-list-add.
"""

import argparse
import csv
import os
import sys
from dotenv import load_dotenv

# Load scraper .env (not repo root)
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from laughtrack.infrastructure.database.connection import get_connection, get_transaction  # noqa: E402
from laughtrack.core.entities.comedian.false_positive_detector import (  # noqa: E402
    PLACEHOLDER_NAMES,
    PLACEHOLDER_SUBSTRINGS,
    STRUCTURAL_KEYWORDS,
)

# Build SQL fragments from the shared Python constants so detection criteria
# are defined in exactly one place (false_positive_detector.py).
_PLACEHOLDER_NAMES = "\n    ".join(f"'{n}'" for n in sorted(PLACEHOLDER_NAMES))

_PLACEHOLDER_SUBSTRINGS = PLACEHOLDER_SUBSTRINGS

_PLACEHOLDER_SUBSTRING_CONDITIONS = "\n        OR ".join(
    f"lower(c.name) LIKE '%{s}%'" for s in _PLACEHOLDER_SUBSTRINGS
)

_STRUCTURAL_KEYWORDS = STRUCTURAL_KEYWORDS

_STRUCTURAL_KEYWORD_CONDITIONS = "\n        OR ".join(
    f"lower(c.name) LIKE '%{kw}%'" for kw in _STRUCTURAL_KEYWORDS
)

# Non-keyword structural patterns (checked separately from keyword substring conditions)
_STRUCTURAL_PATTERN_CONDITIONS = "c.name LIKE '%***%'"

AUDIT_QUERY = f"""
WITH placeholder_comedians AS (
    SELECT
        c.uuid,
        c.name
    FROM comedians c
    WHERE
        -- Known placeholder strings (case-insensitive)
        lower(c.name) = ANY(ARRAY[
            {_PLACEHOLDER_NAMES}
        ])
        OR
        -- Placeholder substrings (e.g. "KRACKPOTS Open Mic Night")
        {_PLACEHOLDER_SUBSTRING_CONDITIONS}
        OR
        -- Short names (< 4 chars) — almost never a real comedian name
        length(trim(c.name)) < 4
)
SELECT
    pc.name                                             AS comedian_name,
    COUNT(li.show_id)                                   AS lineup_count,
    array_agg(DISTINCT li.show_id ORDER BY li.show_id)
        FILTER (WHERE li.show_id IS NOT NULL)           AS all_show_ids,
    (
        SELECT array_agg(x ORDER BY x)
        FROM (
            SELECT DISTINCT li2.show_id AS x
            FROM lineup_items li2
            WHERE li2.comedian_id = pc.uuid
            LIMIT 5
        ) sub
    )                                                   AS sample_show_ids
FROM placeholder_comedians pc
LEFT JOIN lineup_items li ON li.comedian_id = pc.uuid
GROUP BY pc.uuid, pc.name
HAVING COUNT(li.show_id) > 0
ORDER BY lineup_count DESC, comedian_name;
"""

STRUCTURAL_AUDIT_QUERY = f"""
WITH structural_comedians AS (
    SELECT
        c.uuid,
        c.name,
        CASE
            WHEN c.name LIKE '%|%' THEN 'pipe_in_name'
            WHEN length(trim(c.name)) > 60 THEN 'length_gt_60'
            WHEN {_STRUCTURAL_PATTERN_CONDITIONS} THEN 'decoration_pattern'
            ELSE 'non_person_keyword'
        END AS structural_reason
    FROM comedians c
    WHERE
        c.name LIKE '%|%'
        OR length(trim(c.name)) > 60
        OR {_STRUCTURAL_PATTERN_CONDITIONS}
        OR {_STRUCTURAL_KEYWORD_CONDITIONS}
)
SELECT
    sc.name                                             AS comedian_name,
    sc.structural_reason,
    COUNT(li.show_id)                                   AS lineup_count,
    array_agg(DISTINCT li.show_id ORDER BY li.show_id)
        FILTER (WHERE li.show_id IS NOT NULL)           AS all_show_ids,
    (
        SELECT array_agg(x ORDER BY x)
        FROM (
            SELECT DISTINCT li2.show_id AS x
            FROM lineup_items li2
            WHERE li2.comedian_id = sc.uuid
            LIMIT 5
        ) sub
    )                                                   AS sample_show_ids
FROM structural_comedians sc
LEFT JOIN lineup_items li ON li.comedian_id = sc.uuid
GROUP BY sc.uuid, sc.name, sc.structural_reason
HAVING COUNT(li.show_id) > 0
ORDER BY lineup_count DESC, comedian_name;
"""

CLUB_IMPACT_QUERY = f"""
WITH placeholder_comedians AS (
    SELECT c.uuid
    FROM comedians c
    WHERE
        lower(c.name) = ANY(ARRAY[
            {_PLACEHOLDER_NAMES}
        ])
        OR {_PLACEHOLDER_SUBSTRING_CONDITIONS}
        OR length(trim(c.name)) < 4
)
SELECT
    cl.name                         AS club_name,
    cl.id                           AS club_id,
    COUNT(DISTINCT s.id)            AS affected_shows,
    COUNT(li.comedian_id)           AS affected_lineup_items
FROM placeholder_comedians pc
JOIN lineup_items li ON li.comedian_id = pc.uuid
JOIN shows s ON s.id = li.show_id
JOIN clubs cl ON cl.id = s.club_id
GROUP BY cl.id, cl.name
ORDER BY affected_shows DESC, club_name;
"""

# Query to collect UUIDs for deletion — all placeholder + structural comedians
DELETABLE_UUIDS_QUERY = f"""
SELECT DISTINCT c.uuid
FROM comedians c
WHERE
    -- Placeholder names
    lower(c.name) = ANY(ARRAY[
        {_PLACEHOLDER_NAMES}
    ])
    OR {_PLACEHOLDER_SUBSTRING_CONDITIONS}
    OR length(trim(c.name)) < 4
    -- Structural patterns
    OR c.name LIKE '%|%'
    OR length(trim(c.name)) > 60
    OR {_STRUCTURAL_PATTERN_CONDITIONS}
    OR {_STRUCTURAL_KEYWORD_CONDITIONS}
"""

# Per-comedian per-club detail query (for CSV export)
CSV_DETAIL_QUERY = f"""
WITH identified_comedians AS (
    SELECT
        c.uuid,
        c.name,
        CASE
            WHEN lower(c.name) = ANY(ARRAY[{_PLACEHOLDER_NAMES}]) THEN 'placeholder'
            WHEN {_PLACEHOLDER_SUBSTRING_CONDITIONS} THEN 'placeholder'
            WHEN length(trim(c.name)) < 4 THEN 'short_name'
            WHEN c.name LIKE '%|%' THEN 'structural'
            WHEN length(trim(c.name)) > 60 THEN 'structural'
            WHEN {_STRUCTURAL_PATTERN_CONDITIONS} THEN 'structural'
            ELSE 'structural'
        END AS detection_type
    FROM comedians c
    WHERE
        lower(c.name) = ANY(ARRAY[{_PLACEHOLDER_NAMES}])
        OR {_PLACEHOLDER_SUBSTRING_CONDITIONS}
        OR length(trim(c.name)) < 4
        OR c.name LIKE '%|%'
        OR length(trim(c.name)) > 60
        OR {_STRUCTURAL_PATTERN_CONDITIONS}
        OR {_STRUCTURAL_KEYWORD_CONDITIONS}
)
SELECT
    ic.name                                                 AS comedian_name,
    ic.detection_type,
    COUNT(li.show_id)                                       AS lineup_count,
    array_agg(DISTINCT li.show_id ORDER BY li.show_id)
        FILTER (WHERE li.show_id IS NOT NULL)               AS all_show_ids,
    cl.name                                                 AS club_name,
    cl.id                                                   AS club_id,
    COUNT(DISTINCT s.id)                                    AS affected_shows
FROM identified_comedians ic
LEFT JOIN lineup_items li ON li.comedian_id = ic.uuid
LEFT JOIN shows s ON s.id = li.show_id
LEFT JOIN clubs cl ON cl.id = s.club_id
GROUP BY ic.uuid, ic.name, ic.detection_type, cl.id, cl.name
HAVING COUNT(li.show_id) > 0
ORDER BY ic.name, cl.name;
"""


MERGE_CANDIDATES_QUERY = f"""
WITH false_positives AS (
    SELECT c.uuid, c.name
    FROM comedians c
    WHERE
        lower(c.name) = ANY(ARRAY[{_PLACEHOLDER_NAMES}])
        OR {_PLACEHOLDER_SUBSTRING_CONDITIONS}
        OR length(trim(c.name)) < 4
        OR c.name LIKE '%|%'
        OR length(trim(c.name)) > 60
        OR {_STRUCTURAL_PATTERN_CONDITIONS}
        OR {_STRUCTURAL_KEYWORD_CONDITIONS}
),
real_comedians AS (
    SELECT c.uuid, c.name
    FROM comedians c
    WHERE NOT (
        lower(c.name) = ANY(ARRAY[{_PLACEHOLDER_NAMES}])
        OR {_PLACEHOLDER_SUBSTRING_CONDITIONS}
        OR length(trim(c.name)) < 4
        OR c.name LIKE '%|%'
        OR length(trim(c.name)) > 60
        OR {_STRUCTURAL_PATTERN_CONDITIONS}
        OR {_STRUCTURAL_KEYWORD_CONDITIONS}
    )
    AND array_length(regexp_split_to_array(trim(c.name), '\\s+'), 1) = 2
),
all_matches AS (
    SELECT
        fp.uuid  AS fp_uuid,
        fp.name  AS fp_name,
        real.uuid AS real_uuid,
        real.name AS real_name
    FROM false_positives fp
    JOIN real_comedians real
        ON lower(fp.name) LIKE '%' || lower(real.name) || '%'
),
single_matches AS (
    SELECT fp_uuid, fp_name, real_uuid, real_name
    FROM all_matches
    WHERE fp_uuid IN (
        SELECT fp_uuid FROM all_matches GROUP BY fp_uuid HAVING COUNT(*) = 1
    )
)
SELECT
    sm.fp_uuid,
    sm.fp_name,
    sm.real_uuid,
    sm.real_name,
    COUNT(li.show_id) AS lineup_count
FROM single_matches sm
LEFT JOIN lineup_items li ON li.comedian_id = sm.fp_uuid
GROUP BY sm.fp_uuid, sm.fp_name, sm.real_uuid, sm.real_name
ORDER BY lineup_count DESC, sm.fp_name;
"""


def _print_placeholder_section(cur) -> list:
    """Print placeholder/short-name section; returns rows for downstream use."""
    print("=" * 72)
    print("SECTION 1: PLACEHOLDER / SHORT-NAME COMEDIANS")
    print("=" * 72)
    cur.execute(AUDIT_QUERY)
    rows = cur.fetchall()
    if not rows:
        print("No placeholder comedian records found.")
    else:
        total_comedians = len(rows)
        total_lineup_items = sum(r[1] for r in rows)
        print(f"Found {total_comedians} placeholder comedian(s) "
              f"across {total_lineup_items} lineup_item(s).\n")
        print(f"{'Comedian Name':<35} {'Lineup Count':>12}  Sample Show IDs")
        print("-" * 72)
        for name, count, _all_ids, sample_ids in rows:
            sample_str = ", ".join(str(s) for s in (sample_ids or []))
            print(f"{name:<35} {count:>12}  {sample_str}")
    return rows


def _print_structural_section(cur) -> list:
    """Print structural-pattern section; returns rows for downstream use."""
    print("\n" + "=" * 72)
    print("SECTION 2: STRUCTURAL-PATTERN COMEDIANS")
    print("(pipe in name | length > 60 | non-person keyword)")
    print("=" * 72)
    cur.execute(STRUCTURAL_AUDIT_QUERY)
    rows = cur.fetchall()
    if not rows:
        print("No structural-pattern comedian records found.")
    else:
        total_comedians = len(rows)
        total_lineup_items = sum(r[2] for r in rows)
        print(f"Found {total_comedians} structural-pattern comedian(s) "
              f"across {total_lineup_items} lineup_item(s).\n")
        print(f"{'Comedian Name':<45} {'Reason':<22} {'Lineup Count':>12}  Sample Show IDs")
        print("-" * 90)
        for name, reason, count, _all_ids, sample_ids in rows:
            sample_str = ", ".join(str(s) for s in (sample_ids or []))
            print(f"{name:<45} {reason:<22} {count:>12}  {sample_str}")
    return rows


def _print_club_impact(cur) -> list:
    print("\n" + "=" * 72)
    print("CLUB IMPACT (clubs with affected placeholder/short-name shows)")
    print("=" * 72)
    cur.execute(CLUB_IMPACT_QUERY)
    club_rows = cur.fetchall()
    if not club_rows:
        print("No clubs affected.")
    else:
        print(f"\n{'Club Name':<40} {'Club ID':>8}  "
              f"{'Affected Shows':>14}  {'Lineup Items':>12}")
        print("-" * 80)
        for club_name, club_id, affected_shows, affected_items in club_rows:
            print(f"{club_name:<40} {club_id:>8}  "
                  f"{affected_shows:>14}  {affected_items:>12}")
        print(f"\nTotal clubs affected: {len(club_rows)}")
    return club_rows


def _handle_delete(cur, dry_run: bool) -> list[str]:
    """Return list of UUIDs to delete; if not dry_run, perform the deletion atomically.

    On actual deletion, the comedian names are inserted into comedian_deny_list within
    the same transaction so that future scrapes cannot re-insert them.
    """
    cur.execute(DELETABLE_UUIDS_QUERY)
    uuids = [r[0] for r in cur.fetchall()]
    if not uuids:
        print("\nNo records to delete.")
        return []

    if dry_run:
        print(f"\n{'=' * 72}")
        print("DRY-RUN DELETE PREVIEW")
        print(f"{'=' * 72}")
        print(f"Would delete {len(uuids)} comedian record(s) and their lineup_items.")
        print("Pass --delete --confirm to execute.\n")
        for uuid in uuids:
            print(f"  {uuid}")
    else:
        # Fetch names before deletion so they can be written to the deny list.
        cur.execute(
            "SELECT name FROM comedians WHERE uuid = ANY(%s)",
            (uuids,),
        )
        names = [r[0] for r in cur.fetchall()]

        # Delete lineup_items first (FK constraint), then comedians — both in the
        # same transaction (get_transaction) so an interruption between them cannot
        # leave orphaned comedian rows.
        cur.execute(
            "DELETE FROM lineup_items WHERE comedian_id = ANY(%s)",
            (uuids,),
        )
        deleted_items = cur.rowcount
        cur.execute(
            "DELETE FROM comedians WHERE uuid = ANY(%s)",
            (uuids,),
        )
        deleted_comedians = cur.rowcount

        # Record deleted names in the deny list so future scrapes skip them.
        # ON CONFLICT DO NOTHING means re-deleting a name is a no-op.
        from psycopg2.extras import execute_values
        deny_rows = [(name, 'deleted_false_positive', 'audit_script') for name in names]
        execute_values(
            cur,
            """
            INSERT INTO comedian_deny_list (name, reason, added_by)
            VALUES %s
            ON CONFLICT (name) DO NOTHING
            """,
            deny_rows,
        )
        denied_count = len(deny_rows)

        print(f"\nDeleted {deleted_comedians} comedian record(s) "
              f"and {deleted_items} lineup_item(s). "
              f"Added {denied_count} name(s) to comedian_deny_list.")

    return uuids


def _handle_deny_list_add(name: str, reason: str) -> None:
    """Insert *name* into comedian_deny_list with added_by='manual'.

    Prints a clear message whether the insert succeeded or was a no-op.
    """
    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO comedian_deny_list (name, reason, added_by)
                VALUES (%s, %s, 'manual')
                ON CONFLICT (name) DO NOTHING
                """,
                (name, reason),
            )
            inserted = cur.rowcount

    if inserted:
        print(f"Added '{name}' to comedian_deny_list (reason: {reason!r}).")
    else:
        print(f"'{name}' is already in comedian_deny_list — no change.")


def _write_csv(cur, csv_path: str) -> None:
    cur.execute(CSV_DETAIL_QUERY)
    rows = cur.fetchall()
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "comedian_name", "detection_type", "lineup_count",
            "all_show_ids", "club_name", "club_id", "affected_shows",
        ])
        for comedian_name, detection_type, lineup_count, all_show_ids, club_name, club_id, affected_shows in rows:
            show_ids_str = "|".join(str(s) for s in (all_show_ids or []))
            writer.writerow([
                comedian_name,
                detection_type,
                lineup_count,
                show_ids_str,
                club_name or "",
                club_id or "",
                affected_shows,
            ])
    print(f"\nCSV written to: {csv_path} ({len(rows)} row(s))")


def _print_merge_candidates_section(cur) -> list:
    """Print false positives that contain exactly one real two-word comedian name."""
    print("\n" + "=" * 72)
    print("SECTION 4: MERGE CANDIDATES")
    print("(false positives containing exactly one real two-word comedian name)")
    print("=" * 72)
    cur.execute(MERGE_CANDIDATES_QUERY)
    rows = cur.fetchall()
    if not rows:
        print("No merge candidates found.")
    else:
        print(f"Found {len(rows)} merge candidate(s).\n")
        print(f"{'False Positive Name':<50} {'Real Comedian':<30} {'Lineup Count':>12}")
        print("-" * 96)
        for _fp_uuid, fp_name, _real_uuid, real_name, lineup_count in rows:
            print(f"{fp_name:<50} {real_name:<30} {lineup_count:>12}")
    return rows


def _handle_merge_delete(cur, dry_run: bool, merge_rows: list) -> None:
    """Re-point lineup_items to real comedians where possible, then delete all false positives.

    merge_rows: output of MERGE_CANDIDATES_QUERY — false positives with exactly one
    two-word real comedian match. Their lineup_items are re-pointed before deletion.
    False positives with zero or multiple matches are straight-deleted.
    All deleted names are added to comedian_deny_list.
    """
    merge_map = {row[0]: (row[2], row[3]) for row in merge_rows}  # fp_uuid -> (real_uuid, real_name)

    cur.execute(DELETABLE_UUIDS_QUERY)
    all_uuids = [r[0] for r in cur.fetchall()]

    if not all_uuids:
        print("\nNo records to delete.")
        return

    delete_only_uuids = [u for u in all_uuids if u not in merge_map]

    if dry_run:
        print(f"\n{'=' * 72}")
        print("DRY-RUN MERGE+DELETE PREVIEW")
        print(f"{'=' * 72}")
        print(f"Would merge {len(merge_map)} comedian(s) → re-point lineup_items to real comedian.")
        print(f"Would straight-delete {len(delete_only_uuids)} comedian(s) with no real-name match.")
        print("Pass --merge --confirm to execute.\n")
        for fp_uuid, (real_uuid, real_name) in merge_map.items():
            fp_name = next(r[1] for r in merge_rows if r[0] == fp_uuid)
            print(f"  MERGE: '{fp_name}' → '{real_name}'")
    else:
        # Fetch names before deletion for deny list
        cur.execute("SELECT name FROM comedians WHERE uuid = ANY(%s)", (all_uuids,))
        names = [r[0] for r in cur.fetchall()]

        # Re-point lineup_items for merge candidates
        merged_items = 0
        for fp_uuid, (real_uuid, _real_name) in merge_map.items():
            cur.execute(
                "UPDATE lineup_items SET comedian_id = %s WHERE comedian_id = %s",
                (real_uuid, fp_uuid),
            )
            merged_items += cur.rowcount

        # Delete remaining lineup_items (non-merged false positives)
        if delete_only_uuids:
            cur.execute(
                "DELETE FROM lineup_items WHERE comedian_id = ANY(%s)",
                (delete_only_uuids,),
            )
        deleted_items = cur.rowcount if delete_only_uuids else 0

        # Delete all false positive comedian records
        cur.execute("DELETE FROM comedians WHERE uuid = ANY(%s)", (all_uuids,))
        deleted_comedians = cur.rowcount

        # Add all deleted names to deny list
        from psycopg2.extras import execute_values
        deny_rows = [(name, 'deleted_false_positive', 'audit_script') for name in names]
        execute_values(
            cur,
            """
            INSERT INTO comedian_deny_list (name, reason, added_by)
            VALUES %s
            ON CONFLICT (name) DO NOTHING
            """,
            deny_rows,
        )

        print(
            f"\nMerged {len(merge_map)} comedian(s) ({merged_items} lineup_item(s) re-pointed). "
            f"Deleted {deleted_comedians} comedian record(s) and {deleted_items} lineup_item(s). "
            f"Added {len(deny_rows)} name(s) to comedian_deny_list."
        )


def run_audit(delete: bool = False, confirm: bool = False, merge: bool = False, csv_path: str | None = None) -> None:
    merge_rows = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            print("=" * 72)
            print("FALSE-POSITIVE COMEDIAN AUDIT")
            print("=" * 72)

            _print_placeholder_section(cur)
            _print_structural_section(cur)
            _print_club_impact(cur)
            merge_rows = _print_merge_candidates_section(cur)

            if csv_path:
                _write_csv(cur, csv_path)

    if merge:
        dry_run = not confirm
        if dry_run:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    _handle_merge_delete(cur, dry_run=True, merge_rows=merge_rows)
        else:
            with get_transaction() as conn:
                with conn.cursor() as cur:
                    _handle_merge_delete(cur, dry_run=False, merge_rows=merge_rows)
    elif delete:
        dry_run = not confirm
        if dry_run:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    _handle_delete(cur, dry_run=True)
        else:
            with get_transaction() as conn:
                with conn.cursor() as cur:
                    _handle_delete(cur, dry_run=False)

    print("\n" + "=" * 72)
    print("NEXT STEPS")
    print("=" * 72)
    print("1. Review the above — confirm the names listed are indeed false positives.")
    print("2. Note the club IDs with the most affected shows.")
    print("3. After TASK-603 is deployed, re-scrape the affected clubs so that")
    print("   lineup_items are healed (placeholders will be filtered on ingestion).")
    if merge and not confirm:
        print("4. Re-run with --merge --confirm to merge and delete in one pass.")
    elif delete and not confirm:
        print("4. Re-run with --delete --confirm to permanently remove identified records.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the DB for false-positive comedian records.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Show what would be deleted (dry-run unless --confirm is also passed).",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Combined with --delete: actually delete the identified records.",
    )
    parser.add_argument(
        "--csv",
        metavar="PATH",
        dest="csv_path",
        help="Write all findings to a CSV file at PATH.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Re-point lineup_items to real comedians where a unique two-word name match "
             "exists, then delete all false positives. Dry-run unless --confirm is also passed.",
    )
    parser.add_argument(
        "--deny-list-add",
        metavar="NAME",
        dest="deny_list_add",
        help="Insert NAME directly into comedian_deny_list (added_by='manual'). "
             "No-op if the name already exists.",
    )
    parser.add_argument(
        "--deny-list-reason",
        metavar="REASON",
        dest="deny_list_reason",
        default="manual_entry",
        help="Reason string stored with the deny-list entry (default: 'manual_entry'). "
             "Only used with --deny-list-add.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.confirm and not args.delete and not args.merge:
        print("Error: --confirm requires --delete or --merge.", file=sys.stderr)
        sys.exit(1)
    if args.delete and args.merge:
        print("Error: --delete and --merge are mutually exclusive.", file=sys.stderr)
        sys.exit(1)
    if args.deny_list_add:
        _handle_deny_list_add(args.deny_list_add, args.deny_list_reason)
        sys.exit(0)
    run_audit(
        delete=args.delete,
        confirm=args.confirm,
        merge=args.merge,
        csv_path=args.csv_path,
    )
