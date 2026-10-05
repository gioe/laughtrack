#!/usr/bin/env python3
"""Remove the 19 reviewed Big Pine products and activate source title exclusions.

Background: digital products and education inventory were ingested as shows.
What this script does: locks and validates full before-images, deletes only the
reviewed IDs, preserves click records and festival/source/target identities.
Usage: --dry-run (default); --apply --backup /private/path/new.json.
Dry runs execute validation and mutations then roll back. Apply requires durable
private before/after recovery files; they contain user data and must not be committed.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import re
import sys
from pathlib import Path

_root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2 import sql
from scripts.core.repair_annoyance_identity import CHILDREN, save_backup
from scripts.core.repair_seatengine_organizer_venues import digest, rows

PLAN_PATH = _root / "docs/audits/2026-10-05-big-pine-inventory/plan.json"
MARKER = "task_4111_cleanup"
RETIRE_IDS = {
    522199,
    1376633,
    1376635,
    1376636,
    1376637,
    1376638,
    1376639,
    1376640,
    1376641,
    1376642,
    1376643,
    1376644,
    1376645,
    1376646,
    1376647,
    1760217,
    1760218,
    3251332,
    3251333,
}
TABLES = ("clubs", "scraping_sources", "source_targets", "shows", *CHILDREN)
CLICKS = "ticket_purchase_click_events"


def lock_schema(cur):
    cur.execute("SET LOCAL lock_timeout='5s'; SET LOCAL TIME ZONE 'UTC'")
    cur.execute(
        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(sql.SQL(",").join(map(sql.Identifier, TABLES)))
    )
    cur.execute("""SELECT c.conrelid::regclass::text,a.attname,c.confdeltype
        FROM pg_constraint c JOIN LATERAL unnest(c.conkey) k(attnum) ON true
        JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum
        WHERE c.confrelid='shows'::regclass AND c.contype='f'""")
    actual = {(r[0].split(".")[-1].strip('"'), r[1], r[2]) for r in cur.fetchall()}
    if actual != {(table, "show_id", "n" if table == CLICKS else "c") for table in CHILDREN}:
        raise ValueError("Show foreign keys changed; review deletion/recovery coverage")
    cur.execute(
        "SELECT conrelid::regclass::text FROM pg_constraint WHERE contype='f' AND confrelid=ANY(%s::regclass[])",
        (list(CHILDREN),),
    )
    if cur.fetchall():
        raise ValueError("Child tables have inbound references; review recovery coverage")
    schema = {}
    for table in TABLES:
        cur.execute(
            "SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum",
            (table,),
        )
        schema[table] = cur.fetchall()
    return schema


def snapshot(cur, plan, click_ids=None):
    cur.execute("SELECT id FROM shows WHERE club_id=573")
    ids = set(plan["inventory_ids"]) | {r[0] for r in cur.fetchall()}
    state = {
        "shows": rows(cur, "shows", "id", ids),
        "clubs": rows(cur, "clubs", "id", [573]),
        "scraping_sources": rows(cur, "scraping_sources", "id", [360, 3126, 7146]),
        "source_targets": rows(cur, "source_targets", "id", [1, 2]),
    }
    state.update({table: rows(cur, table, "show_id", ids) for table in CHILDREN})
    if click_ids is not None:
        state[CLICKS] = rows(cur, CLICKS, "id", click_ids)
    return state


def validate_plan(plan):
    if (plan["task_id"], plan["club_id"], plan["source_id"]) != (4111, 573, 360):
        raise ValueError("Unexpected task/source identity")
    if set(plan["retire_ids"]) != RETIRE_IDS or len(plan["retire_ids"]) != 19:
        raise ValueError("Deletion cohort must be exactly the 19 reviewed IDs")
    if not RETIRE_IDS <= set(plan["inventory_ids"]):
        raise ValueError("Missing reviewed inventory")
    patterns = plan["exclude_title_patterns"]
    if not patterns or any(not p.startswith("^\\s*") or not p.endswith("\\s*$") for p in patterns):
        raise ValueError("Source exclusions must be anchored reviewed titles")
    for pattern in patterns:
        re.compile(pattern, re.IGNORECASE)
    if set(plan["before_hashes"]) != set(TABLES) or set(plan["expected_counts"]) != set(TABLES):
        raise ValueError("Missing dependency before-images")


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    before = snapshot(cur, plan)
    source = next((r for r in before["scraping_sources"] if r["id"] == 360), None)
    if source is None or source["club_id"] != 573 or not source["enabled"]:
        raise ValueError("Festival source changed")
    metadata = source["metadata"] or {}
    if metadata.get(MARKER) == digest(plan):
        if metadata.get("exclude_title_patterns") != plan["exclude_title_patterns"] or any(
            r["id"] in RETIRE_IDS for r in before["shows"]
        ):
            raise ValueError("Previously applied cleanup drifted")
        return {"already_applied": True, "before": before, "after": before}
    for table in TABLES:
        if (
            len(before[table]) != plan["expected_counts"][table]
            or digest(before[table]) != plan["before_hashes"][table]
        ):
            raise ValueError(f"{table} before-image changed; re-review before applying")
    if {r["id"] for r in before["shows"]} != set(plan["inventory_ids"]):
        raise ValueError("Inventory cohort changed")
    if any(r["club_id"] != 573 for r in before["shows"]) or not before["clubs"][0]["visible"]:
        raise ValueError("Festival identity changed")
    recovery = {"plan": plan, "schema": schema, "before": before, "already_applied": False}
    if backup_path:
        save_backup(backup_path, recovery)
    patched = dict(metadata, exclude_title_patterns=plan["exclude_title_patterns"], **{MARKER: digest(plan)})
    cur.execute("UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=360 AND club_id=573", (json.dumps(patched),))
    if cur.rowcount != 1:
        raise ValueError("Source update count changed")
    cur.execute("DELETE FROM shows WHERE club_id=573 AND id=ANY(%s) RETURNING id", (sorted(RETIRE_IDS),))
    if {r[0] for r in cur.fetchall()} != RETIRE_IDS:
        raise ValueError("Deletion count changed")
    cur.execute("UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=573) WHERE id=573")
    after = snapshot(cur, plan, [r["id"] for r in before[CLICKS]])
    expected = deepcopy(before)
    expected["shows"] = [r for r in expected["shows"] if r["id"] not in RETIRE_IDS]
    for table in CHILDREN:
        if table == CLICKS:
            for row in expected[table]:
                if row["show_id"] in RETIRE_IDS:
                    row["show_id"] = None
        else:
            expected[table] = [r for r in expected[table] if r["show_id"] not in RETIRE_IDS]
    expected["clubs"][0]["total_shows"] = len(expected["shows"])
    for row in expected["scraping_sources"]:
        if row["id"] == 360:
            row["metadata"] = patched
            if "updated_at" in row:
                row["updated_at"] = next(r["updated_at"] for r in after["scraping_sources"] if r["id"] == 360)
    for table in TABLES:
        if sorted(after[table], key=lambda r: json.dumps(r, sort_keys=True)) != sorted(
            expected[table], key=lambda r: json.dumps(r, sort_keys=True)
        ):
            raise ValueError(f"Unexpected after-image: {table}")
    recovery["after"] = after
    if backup_path:
        save_backup(str(backup_path) + ".after.json", recovery)
    return recovery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private --backup path")
    from dotenv import load_dotenv

    load_dotenv(_root / ".env")
    from laughtrack.adapters.db import get_transaction

    plan = json.loads(args.plan.read_text())
    with get_transaction() as connection:
        with connection.cursor() as cur:
            result = repair(cur, plan, args.backup if args.apply else None)
        print(
            json.dumps(
                {
                    "mode": "apply" if args.apply else "PLAN",
                    "already_applied": result["already_applied"],
                    "before": {t: len(v) for t, v in result["before"].items()},
                    "after": {t: len(v) for t, v in result["after"].items()},
                }
            )
        )
        if not args.apply:
            connection.rollback()
            print("PLAN: rolled back")
    if args.apply:
        print("COMMITTED: verified Big Pine inventory cleanup")


if __name__ == "__main__":
    main()
