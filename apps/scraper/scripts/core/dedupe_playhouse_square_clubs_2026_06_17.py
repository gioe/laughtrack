#!/usr/bin/env python3
"""
Dedupe the duplicate Playhouse Square (Cleveland) venue clubs (TASK-2942).

The PHS venue clubs accumulated duplicates over time:
  - Connor Palace: club 5058 "Connor Palace at Playhouse Square" (canonical) and
    club 5071 "Connor Palace - Cleveland" (duplicate).
  - Ohio Theatre: the Ohio Theatre at Playhouse Square was renamed "Mimi Ohio
    Theatre" (the name the PHS feed itself uses). Club 5394 "Mimi Ohio Theatre"
    is canonical; clubs 5338 "Ohio Theatre at PlayhouseSquare" and 5392
    "Ohio Theatre - Playhouse Square" are duplicates of the same physical room.

For each (canonical, duplicate) pair this script, in one transaction:
  1. migrates duplicate shows to the canonical club (deleting those that would
     collide on the (club_id, date, room) unique index),
  2. migrates favorite_clubs rows to the canonical club (dropping rows that
     already favorite the canonical club),
  3. disables the duplicate club's scraping_sources so the nightly scrape stops
     re-creating shows under it,
  4. hides + closes the duplicate club and recomputes total_shows on both.

It is idempotent: once a duplicate is hidden/closed it is skipped on re-run. A
recovery log of every touched row is written under docs/audits/.

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/dedupe_playhouse_square_clubs_2026_06_17.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/dedupe_playhouse_square_clubs_2026_06_17.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction


@dataclass(frozen=True)
class MergeTarget:
    canonical_club_id: int
    duplicate_club_id: int
    canonical_name: str
    duplicate_name: str
    rationale: str


_TARGETS = [
    MergeTarget(
        canonical_club_id=5058,
        duplicate_club_id=5071,
        canonical_name="Connor Palace at Playhouse Square",
        duplicate_name="Connor Palace - Cleveland",
        rationale="Same physical venue (Connor Palace, Playhouse Square). Keep 5058.",
    ),
    MergeTarget(
        canonical_club_id=5394,
        duplicate_club_id=5338,
        canonical_name="Mimi Ohio Theatre",
        duplicate_name="Ohio Theatre at PlayhouseSquare",
        rationale="Ohio Theatre at Playhouse Square was renamed Mimi Ohio Theatre "
        "(the name the PHS feed uses). Keep 5394.",
    ),
    MergeTarget(
        canonical_club_id=5394,
        duplicate_club_id=5392,
        canonical_name="Mimi Ohio Theatre",
        duplicate_name="Ohio Theatre - Playhouse Square",
        rationale="Ohio Theatre at Playhouse Square was renamed Mimi Ohio Theatre "
        "(the name the PHS feed uses). Keep 5394.",
    ),
]

_RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-2942-phs-club-dedupe-log.json"


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _fetch_club_snapshot(cur: RealDictCursor, club_id: int) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT id, name, address, website, city, state, timezone, visible,
               total_shows, status, closed_at
        FROM clubs
        WHERE id = %s
        FOR UPDATE
        """,
        (club_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _already_merged(duplicate: dict[str, Any]) -> bool:
    """A duplicate already folded by a prior run is hidden + closed."""
    return (not duplicate["visible"]) and duplicate.get("status") == "closed"


def _validate_target(
    cur: RealDictCursor, target: MergeTarget
) -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = _fetch_club_snapshot(cur, target.canonical_club_id)
    duplicate = _fetch_club_snapshot(cur, target.duplicate_club_id)
    problems = []
    if canonical is None:
        problems.append(f"canonical club {target.canonical_club_id} not found")
    elif canonical["name"] != target.canonical_name:
        problems.append(
            f"club {target.canonical_club_id} name is {canonical['name']!r}, "
            f"expected {target.canonical_name!r}"
        )
    if duplicate is None:
        problems.append(f"duplicate club {target.duplicate_club_id} not found")
    elif duplicate["name"] != target.duplicate_name and not _already_merged(duplicate):
        problems.append(
            f"club {target.duplicate_club_id} name is {duplicate['name']!r}, "
            f"expected {target.duplicate_name!r}"
        )
    if problems:
        raise RuntimeError("; ".join(problems))
    return canonical, duplicate


def _fetch_duplicate_show_plan(
    cur: RealDictCursor, target: MergeTarget
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cur.execute(
        """
        SELECT s_dup.id AS duplicate_show_id,
               s_dup.name AS duplicate_name,
               s_dup.date,
               s_dup.room,
               s_can.id AS canonical_show_id
        FROM shows s_dup
        LEFT JOIN shows s_can
          ON s_can.club_id = %s
         AND s_can.date = s_dup.date
         AND s_can.room IS NOT DISTINCT FROM s_dup.room
        WHERE s_dup.club_id = %s
        ORDER BY s_dup.date, s_dup.id
        """,
        (target.canonical_club_id, target.duplicate_club_id),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conflicting = [r for r in rows if r["canonical_show_id"] is not None]
    migratable = [r for r in rows if r["canonical_show_id"] is None]
    return conflicting, migratable


def _fetch_favorite_plan(cur: RealDictCursor, target: MergeTarget) -> dict[str, int]:
    cur.execute(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE NOT EXISTS (
                    SELECT 1 FROM favorite_clubs f2
                    WHERE f2.club_id = %s AND f2.profile_id = f.profile_id
                )
            ) AS migratable,
            COUNT(*) FILTER (
                WHERE EXISTS (
                    SELECT 1 FROM favorite_clubs f2
                    WHERE f2.club_id = %s AND f2.profile_id = f.profile_id
                )
            ) AS already_on_canonical
        FROM favorite_clubs f
        WHERE f.club_id = %s
        """,
        (target.canonical_club_id, target.canonical_club_id, target.duplicate_club_id),
    )
    row = cur.fetchone()
    return {
        "migratable": int(row["migratable"] or 0),
        "already_on_canonical": int(row["already_on_canonical"] or 0),
    }


def _apply_merge(cur: RealDictCursor, target: MergeTarget) -> None:
    # 1. Drop duplicate shows that would collide with the canonical club on the
    #    (club_id, date, room) unique index, then repoint the rest.
    cur.execute(
        """
        DELETE FROM shows s_dup
        USING shows s_can
        WHERE s_dup.club_id = %s
          AND s_can.club_id = %s
          AND s_can.date = s_dup.date
          AND s_can.room IS NOT DISTINCT FROM s_dup.room
        """,
        (target.duplicate_club_id, target.canonical_club_id),
    )
    cur.execute(
        "UPDATE shows SET club_id = %s WHERE club_id = %s",
        (target.canonical_club_id, target.duplicate_club_id),
    )

    # 2. Migrate favorites (PK is (profile_id, club_id)); move those not already
    #    favoriting the canonical club, then drop the leftover duplicates.
    cur.execute(
        """
        UPDATE favorite_clubs f
        SET club_id = %s
        WHERE f.club_id = %s
          AND NOT EXISTS (
              SELECT 1 FROM favorite_clubs f2
              WHERE f2.club_id = %s AND f2.profile_id = f.profile_id
          )
        """,
        (target.canonical_club_id, target.duplicate_club_id, target.canonical_club_id),
    )
    cur.execute("DELETE FROM favorite_clubs WHERE club_id = %s", (target.duplicate_club_id,))

    # 3. Disable the duplicate's scraping_sources so the nightly scrape stops
    #    re-creating shows under the now-hidden club.
    cur.execute(
        "UPDATE scraping_sources SET enabled = false WHERE club_id = %s",
        (target.duplicate_club_id,),
    )

    # 4. Hide + close the duplicate club; recompute total_shows on both.
    cur.execute(
        """
        UPDATE clubs
        SET name = %s,
            visible = false,
            status = 'closed',
            closed_at = COALESCE(closed_at, NOW())
        WHERE id = %s
        """,
        (
            f"{target.duplicate_name} (duplicate of club {target.canonical_club_id})",
            target.duplicate_club_id,
        ),
    )
    cur.execute(
        """
        UPDATE clubs
        SET total_shows = (SELECT COUNT(*) FROM shows WHERE shows.club_id = clubs.id)
        WHERE id IN (%s, %s)
        """,
        (target.canonical_club_id, target.duplicate_club_id),
    )


def run(dry_run: bool) -> dict[str, Any]:
    log: dict[str, Any] = {
        "task_id": 2942,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "merges": [],
    }

    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for target in _TARGETS:
                canonical, duplicate = _validate_target(cur, target)
                if _already_merged(duplicate):
                    log["merges"].append(
                        {
                            "canonical_club_id": target.canonical_club_id,
                            "duplicate_club_id": target.duplicate_club_id,
                            "skipped": "already merged (hidden + closed)",
                        }
                    )
                    continue

                conflicting, migratable = _fetch_duplicate_show_plan(cur, target)
                favorites = _fetch_favorite_plan(cur, target)
                log["merges"].append(
                    {
                        "canonical_club_before": canonical,
                        "duplicate_club_before": duplicate,
                        "rationale": target.rationale,
                        "conflicting_duplicate_shows_deleted": conflicting,
                        "duplicate_shows_migrated": migratable,
                        "deleted_show_count": len(conflicting),
                        "migrated_show_count": len(migratable),
                        "favorites_migrated": favorites["migratable"],
                        "favorites_already_on_canonical_deleted": favorites["already_on_canonical"],
                    }
                )
                if not dry_run:
                    _apply_merge(cur, target)
            if dry_run:
                conn.rollback()
            else:
                _RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                _RECOVERY_LOG_PATH.write_text(
                    json.dumps(log, indent=2, sort_keys=True, default=_json_default) + "\n",
                    encoding="utf-8",
                )
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description="Dedupe duplicate Playhouse Square venue clubs (TASK-2942).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log = run(dry_run=args.dry_run)
    print(json.dumps(log, indent=2, sort_keys=True, default=_json_default))
    if args.dry_run:
        print("DRY RUN: no database rows were changed and no recovery log was written.")
    else:
        print(f"Wrote recovery log: {_RECOVERY_LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
