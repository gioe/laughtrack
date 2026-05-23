#!/usr/bin/env python3
"""
Delete stale Tixr ticket rows whose tier names still carry performance-time
suffixes after TASK-2400.

Background
----------
TASK-2400 changed the Tixr group-events split path so emitted ticket tier names
drop redundant performance-time suffixes such as "General Admission - Friday
7:30pm". Previously-scraped split shows can now carry both the old suffixed row
and the new bare-name row because tickets are upserted on (show_id, type).

What this script does
---------------------
1. Finds Tixr ticket rows whose type ends with
   " - <weekday> <h[:mm]><am|pm>".
2. Deletes only rows where the same show already has a bare-name ticket row
   matching the suffix-stripped type.
3. Reports, but never deletes, suffixed rows that do not yet have a same-show
   bare-name replacement.

Idempotent: after the first real run, the deletable row count is zero.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/cleanup_stale_tixr_suffixed_ticket_rows_2026_05_22.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/cleanup_stale_tixr_suffixed_ticket_rows_2026_05_22.py
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

from laughtrack.adapters.db import get_transaction


TASK_ID = 2402
TARGET_CLUB_ID = 171
TARGET_CLUB_NAME = "Laugh Factory Covina"

# Mirrors TixrClient._PERFORMANCE_TIME_SUFFIX_RE. PostgreSQL's regexp engine
# does not support \d, so use [0-9] explicitly.
PERFORMANCE_TIME_SUFFIX_SQL_RE = (
    r"\s+[-–—]\s*"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|mon|tues|tue|wed|thurs|thur|thu|fri|sat|sun)"
    r"\s+[0-9]{1,2}(:[0-9]{2})?"
    r"\s*(am|pm)\s*$"
)

TIXR_TICKET_SCOPE_SQL = """
    (COALESCE(t.purchase_url, '') ILIKE '%%tixr.com%%'
     OR COALESCE(s.show_page_url, '') ILIKE '%%tixr.com%%'
     OR COALESCE(s.last_scraped_by, '') ILIKE '%%tixr%%')
"""

_CANDIDATE_CTE = f"""
    WITH suffixed AS (
        SELECT
            t.id,
            t.show_id,
            s.club_id,
            c.name AS club_name,
            s.date,
            t.type AS suffixed_type,
            regexp_replace(t.type, %s, '', 'i') AS bare_type,
            t.price,
            t.purchase_url,
            EXISTS (
                SELECT 1
                FROM tickets bare
                WHERE bare.show_id = t.show_id
                  AND bare.type = regexp_replace(t.type, %s, '', 'i')
            ) AS has_bare_replacement
        FROM tickets t
        JOIN shows s ON s.id = t.show_id
        JOIN clubs c ON c.id = s.club_id
        WHERE t.type ~* %s
          AND {TIXR_TICKET_SCOPE_SQL}
    )
"""

COUNT_SQL = _CANDIDATE_CTE + """
    SELECT
        COUNT(*) FILTER (WHERE has_bare_replacement) AS deletable,
        COUNT(*) FILTER (WHERE NOT has_bare_replacement) AS protected,
        COUNT(*) FILTER (WHERE has_bare_replacement AND club_id = %s) AS target_deletable,
        COUNT(*) FILTER (WHERE NOT has_bare_replacement AND club_id = %s) AS target_protected
    FROM suffixed
"""

SAMPLE_SQL = _CANDIDATE_CTE + """
    SELECT id, show_id, club_id, club_name, date, suffixed_type, bare_type, has_bare_replacement
    FROM suffixed
    ORDER BY has_bare_replacement DESC, club_id, date, suffixed_type
    LIMIT %s
"""

TARGET_CLUB_SUMMARY_SQL = _CANDIDATE_CTE + """
    SELECT
        show_id,
        date,
        COUNT(*) FILTER (WHERE has_bare_replacement) AS deletable,
        COUNT(*) FILTER (WHERE NOT has_bare_replacement) AS protected
    FROM suffixed
    WHERE club_id = %s
    GROUP BY show_id, date
    ORDER BY date, show_id
"""

DELETE_SQL = _CANDIDATE_CTE + """
    DELETE FROM tickets doomed
    USING suffixed
    WHERE doomed.id = suffixed.id
      AND suffixed.has_bare_replacement
    RETURNING doomed.id, doomed.show_id, suffixed.club_id, suffixed.suffixed_type, suffixed.bare_type
"""


def _query_counts(cur) -> tuple[int, int, int, int]:
    cur.execute(
        COUNT_SQL,
        (
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            TARGET_CLUB_ID,
            TARGET_CLUB_ID,
        ),
    )
    row = cur.fetchone()
    return tuple(int(v or 0) for v in row)


def _print_counts(label: str, counts: tuple[int, int, int, int]) -> None:
    deletable, protected, target_deletable, target_protected = counts
    print(f"=== {label} ===")
    print(f"  all Tixr suffixed rows with same-show bare replacement: {deletable}")
    print(f"  all Tixr suffixed rows without same-show bare replacement: {protected}")
    print(f"  club {TARGET_CLUB_ID} ({TARGET_CLUB_NAME}) deletable: {target_deletable}")
    print(f"  club {TARGET_CLUB_ID} ({TARGET_CLUB_NAME}) protected: {target_protected}")


def _print_sample(cur, limit: int) -> None:
    cur.execute(
        SAMPLE_SQL,
        (
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            limit,
        ),
    )
    rows = cur.fetchall()
    if not rows:
        print("\nNo suffixed Tixr ticket rows found.")
        return

    print("\n=== SAMPLE ===")
    for row in rows:
        ticket_id, show_id, club_id, club_name, date, suffixed, bare, has_bare = row
        action = "DELETE" if has_bare else "PROTECT"
        print(
            f"  {action:<7} ticket={ticket_id} show={show_id} club={club_id} "
            f"{club_name!r} date={date} {suffixed!r} -> {bare!r}"
        )


def _print_target_summary(cur) -> None:
    cur.execute(
        TARGET_CLUB_SUMMARY_SQL,
        (
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            PERFORMANCE_TIME_SUFFIX_SQL_RE,
            TARGET_CLUB_ID,
        ),
    )
    rows = cur.fetchall()
    if not rows:
        print(f"\nNo suffixed Tixr ticket rows found for club {TARGET_CLUB_ID}.")
        return

    print(f"\n=== CLUB {TARGET_CLUB_ID} SUMMARY ===")
    for show_id, date, deletable, protected in rows:
        print(
            f"  show={show_id} date={date} deletable={int(deletable or 0)} "
            f"protected={int(protected or 0)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete stale day-time-suffixed Tixr ticket rows with bare replacements."
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--sample-limit", type=int, default=20, help="Number of candidate rows to print")
    args = parser.parse_args()

    with get_transaction() as conn:
        with conn.cursor() as cur:
            before = _query_counts(cur)
            _print_counts("BEFORE", before)
            _print_sample(cur, args.sample_limit)
            _print_target_summary(cur)

            if args.dry_run:
                print("\n--dry-run: no DB write performed.")
                return 0

            cur.execute(
                DELETE_SQL,
                (
                    PERFORMANCE_TIME_SUFFIX_SQL_RE,
                    PERFORMANCE_TIME_SUFFIX_SQL_RE,
                    PERFORMANCE_TIME_SUFFIX_SQL_RE,
                ),
            )
            deleted_rows = cur.fetchall()
            print(f"\nDeleted {len(deleted_rows)} stale suffixed Tixr ticket rows.")

            expected_deleted = before[0]
            if len(deleted_rows) != expected_deleted:
                raise RuntimeError(
                    f"planned {expected_deleted} deletions, but deleted {len(deleted_rows)}"
                )

            after = _query_counts(cur)
            print()
            _print_counts("AFTER", after)
            _print_target_summary(cur)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
