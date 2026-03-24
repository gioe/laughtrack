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
  2. Name length < 4 characters (single-name tokens that are almost never real comedian names)

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


_PLACEHOLDER_NAMES = """
    'tba', 'tbd', 'to be announced', 'to be determined',
    'special guest', 'special guests',
    'surprise guest', 'surprise act', 'mystery guest',
    'comedy show', 'various artists',
    'headliner', 'featured comedian', 'local comedian',
    'guest comedian', 'guest',
    'open mic', 'host', 'mc', 'emcee',
    'opener', 'opener tbd',
    'headliner tbd', 'lineup tba',
    'more tba', 'plus more', 'and more', 'and special guests',
    'comedian tba', 'comedian tbd',
    'comics tba', 'comics tbd'
"""

_STRUCTURAL_KEYWORDS = (
    'revue', 'burlesque', 'variety', 'showcase', 'production',
    'presents', 'festival', 'extravaganza', 'theatre', 'theater', 'entertainment',
)

_STRUCTURAL_KEYWORD_CONDITIONS = "\n        OR ".join(
    f"lower(c.name) LIKE '%{kw}%'" for kw in _STRUCTURAL_KEYWORDS
)

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
            ELSE 'non_person_keyword'
        END AS structural_reason
    FROM comedians c
    WHERE
        c.name LIKE '%|%'
        OR length(trim(c.name)) > 60
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
    OR length(trim(c.name)) < 4
    -- Structural patterns
    OR c.name LIKE '%|%'
    OR length(trim(c.name)) > 60
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
            WHEN length(trim(c.name)) < 4 THEN 'short_name'
            WHEN c.name LIKE '%|%' THEN 'structural'
            WHEN length(trim(c.name)) > 60 THEN 'structural'
            ELSE 'structural'
        END AS detection_type
    FROM comedians c
    WHERE
        lower(c.name) = ANY(ARRAY[{_PLACEHOLDER_NAMES}])
        OR length(trim(c.name)) < 4
        OR c.name LIKE '%|%'
        OR length(trim(c.name)) > 60
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
    """Return list of UUIDs to delete; if not dry_run, perform the deletion atomically."""
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
        print(f"\nDeleted {deleted_comedians} comedian record(s) "
              f"and {deleted_items} lineup_item(s).")

    return uuids


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


def run_audit(delete: bool = False, confirm: bool = False, csv_path: str | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            print("=" * 72)
            print("FALSE-POSITIVE COMEDIAN AUDIT")
            print("=" * 72)

            _print_placeholder_section(cur)
            _print_structural_section(cur)
            _print_club_impact(cur)

            if csv_path:
                _write_csv(cur, csv_path)

    if delete:
        dry_run = not confirm
        if dry_run:
            # Dry-run only needs a read connection to fetch the UUIDs preview
            with get_connection() as conn:
                with conn.cursor() as cur:
                    _handle_delete(cur, dry_run=True)
        else:
            # Actual deletion: wrap both DELETEs in a single transaction so an
            # interruption between them cannot leave orphaned comedian rows.
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
    if delete and not confirm:
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
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.confirm and not args.delete:
        print("Error: --confirm requires --delete.", file=sys.stderr)
        sys.exit(1)
    run_audit(
        delete=args.delete,
        confirm=args.confirm,
        csv_path=args.csv_path,
    )
