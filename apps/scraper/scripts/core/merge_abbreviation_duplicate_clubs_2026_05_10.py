#!/usr/bin/env python3
"""
Merge obvious club-name abbreviation duplicates found by TASK-2114.

This is intentionally a narrow production data cleanup, not scraper
normalization. It audits the requested abbreviation families (Ft./Fort,
St./Saint, Mt./Mount, and &/and), merges the confirmed Fort Lauderdale Improv
duplicate, and writes a recovery log with the exact rows and show IDs touched.

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/merge_abbreviation_duplicate_clubs_2026_05_10.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/merge_abbreviation_duplicate_clubs_2026_05_10.py
"""

from __future__ import annotations

import argparse
import json
import re
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
        canonical_club_id=53,
        duplicate_club_id=460,
        canonical_name="Fort Lauderdale Improv",
        duplicate_name="Ft. Lauderdale Improv",
        rationale=(
            "Same physical venue. Keep canonical row 53 because it has full "
            "address/city/state metadata; fold row 460 because it is a stub "
            "created from abbreviated tour-date text."
        ),
    ),
]

_RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-2114-club-merge-log.json"


def _normalize_name(name: str) -> str:
    normalized = name.lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"(?<![a-z0-9])ft\.?(?![a-z0-9])", "fort", normalized)
    normalized = re.sub(r"(?<![a-z0-9])st\.?(?![a-z0-9])", "saint", normalized)
    normalized = re.sub(r"(?<![a-z0-9])mt\.?(?![a-z0-9])", "mount", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _has_requested_abbreviation_signal(left: str, right: str) -> bool:
    pairs = [
        (r"(?<![a-z0-9])ft\.?(?![a-z0-9])", r"\bfort\b"),
        (r"(?<![a-z0-9])st\.?(?![a-z0-9])", r"\bsaint\b"),
        (r"(?<![a-z0-9])mt\.?(?![a-z0-9])", r"\bmount\b"),
        (r"&", r"\band\b"),
    ]
    left_l = left.lower()
    right_l = right.lower()
    return any(
        (re.search(short, left_l) and re.search(long, right_l))
        or (re.search(short, right_l) and re.search(long, left_l))
        for short, long in pairs
    )


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _fetch_abbreviation_groups(cur: RealDictCursor) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT c.id, c.name, c.address, c.city, c.state, c.status, c.visible,
               c.chain_id, c.total_shows,
               COUNT(s.id) AS actual_show_count,
               COUNT(*) FILTER (WHERE s.date >= NOW()) AS upcoming_show_count
        FROM clubs c
        LEFT JOIN shows s ON s.club_id = c.id
        GROUP BY c.id
        ORDER BY c.id
        """
    )
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in cur.fetchall():
        groups.setdefault(_normalize_name(row["name"]), []).append(dict(row))

    matches: list[dict[str, Any]] = []
    for normalized_name, rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        names = [row["name"] for row in rows]
        if not any(
            _has_requested_abbreviation_signal(left, right)
            for i, left in enumerate(names)
            for right in names[i + 1 :]
        ):
            continue
        matches.append({"normalized_name": normalized_name, "rows": rows})
    return matches


def _fetch_club_snapshot(cur: RealDictCursor, club_id: int) -> dict[str, Any]:
    cur.execute(
        """
        SELECT id, name, address, website, city, state, country, phone_number,
               timezone, visible, total_shows, has_image, status, club_type,
               closed_at, chain_id
        FROM clubs
        WHERE id = %s
        FOR UPDATE
        """,
        (club_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Expected club {club_id} to exist")
    return dict(row)


def _validate_target(cur: RealDictCursor, target: MergeTarget) -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = _fetch_club_snapshot(cur, target.canonical_club_id)
    duplicate = _fetch_club_snapshot(cur, target.duplicate_club_id)
    problems = []
    if canonical["name"] != target.canonical_name:
        problems.append(f"club {target.canonical_club_id} name is {canonical['name']!r}")
    if duplicate["name"] != target.duplicate_name:
        problems.append(f"club {target.duplicate_club_id} name is {duplicate['name']!r}")
    if not canonical["visible"] or canonical["status"] != "active":
        problems.append(f"canonical club {target.canonical_club_id} is not active/visible")
    if not duplicate["visible"] or duplicate["status"] != "active":
        problems.append(f"duplicate club {target.duplicate_club_id} is not active/visible")
    if _normalize_name(canonical["name"]) != _normalize_name(duplicate["name"]):
        problems.append("normalized names no longer match")
    if problems:
        raise RuntimeError("; ".join(problems))
    return canonical, duplicate


def _fetch_duplicate_show_plan(cur: RealDictCursor, target: MergeTarget) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cur.execute(
        """
        SELECT s_dup.id AS duplicate_show_id,
               s_dup.name AS duplicate_name,
               s_dup.date,
               s_dup.room,
               s_dup.show_page_url AS duplicate_show_page_url,
               s_can.id AS canonical_show_id,
               s_can.name AS canonical_name,
               s_can.show_page_url AS canonical_show_page_url,
               COUNT(DISTINCT li.id) AS duplicate_lineup_item_count,
               COUNT(DISTINCT t.id) AS duplicate_ticket_count
        FROM shows s_dup
        LEFT JOIN shows s_can
          ON s_can.club_id = %s
         AND s_can.date = s_dup.date
         AND s_can.room IS NOT DISTINCT FROM s_dup.room
        LEFT JOIN lineup_items li ON li.show_id = s_dup.id
        LEFT JOIN tickets t ON t.show_id = s_dup.id
        WHERE s_dup.club_id = %s
        GROUP BY s_dup.id, s_can.id
        ORDER BY s_dup.date, s_dup.id
        """,
        (target.canonical_club_id, target.duplicate_club_id),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conflicting = [row for row in rows if row["canonical_show_id"] is not None]
    migratable = [row for row in rows if row["canonical_show_id"] is None]
    return conflicting, migratable


def _apply_merge(cur: RealDictCursor, target: MergeTarget) -> None:
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
    cur.execute(
        """
        UPDATE clubs
        SET name = %s,
            visible = false,
            status = 'closed',
            closed_at = COALESCE(closed_at, NOW())
        WHERE id = %s
        """,
        (f"{target.duplicate_name} (duplicate of club {target.canonical_club_id})", target.duplicate_club_id),
    )
    cur.execute(
        """
        UPDATE clubs
        SET total_shows = (
            SELECT COUNT(*)
            FROM shows
            WHERE shows.club_id = clubs.id
        )
        WHERE id IN (%s, %s)
        """,
        (target.canonical_club_id, target.duplicate_club_id),
    )


def run(dry_run: bool) -> dict[str, Any]:
    log: dict[str, Any] = {
        "task_id": 2114,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "audit_families": ["Ft./Fort", "St./Saint", "Mt./Mount", "&/and"],
        "abbreviation_groups": [],
        "merges": [],
    }

    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            log["abbreviation_groups"] = _fetch_abbreviation_groups(cur)
            for target in _TARGETS:
                canonical, duplicate = _validate_target(cur, target)
                conflicting, migratable = _fetch_duplicate_show_plan(cur, target)
                merge_log = {
                    "canonical_club_before": canonical,
                    "duplicate_club_before": duplicate,
                    "rationale": target.rationale,
                    "conflicting_duplicate_shows_deleted": conflicting,
                    "duplicate_shows_migrated": migratable,
                    "deleted_show_count": len(conflicting),
                    "migrated_show_count": len(migratable),
                    "total_duplicate_show_count": len(conflicting) + len(migratable),
                }
                log["merges"].append(merge_log)
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
    parser = argparse.ArgumentParser()
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
