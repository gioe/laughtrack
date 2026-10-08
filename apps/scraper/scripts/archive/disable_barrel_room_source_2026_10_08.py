#!/usr/bin/env python3
"""TASK-4142: disable the stale Barrel Room Classic source, preserving history.

The venue-linked replacement inventory is music/email products, not comedy.
Only source77.enabled changes; updated_at is refreshed by the database trigger.
Usage: --plan reviewed-plan.json [--apply --backup /private/new.json]
Recovery: --plan reviewed-plan.json --restore /private/new.json.after.json
Default dry-run rolls back. Recovery refuses affected-state or schema drift.
Private before/after files contain user relationships: never commit them.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.core.repair_annoyance_identity import (
    lock_schema as lock_show_schema,
    plan_hash as digest,
    save_backup,
    snapshot as snapshot_shows,
)

SOURCE_ID = 77
CLUB_ID = 88
URL = "https://www.barrelroompdx.com/events"


def lock_schema(cur):
    schema = lock_show_schema(cur)
    cur.execute("LOCK TABLE clubs IN SHARE ROW EXCLUSIVE MODE")
    cur.execute("""SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute
        WHERE attrelid='clubs'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum""")
    schema["clubs"] = json.loads(json.dumps(cur.fetchall()))
    return schema


def snapshot(cur):
    result = snapshot_shows(cur, dict(club_id=CLUB_ID, source_id=SOURCE_ID, expected_shows={}))
    cur.execute("SELECT to_jsonb(c) FROM clubs c WHERE id=%s", (CLUB_ID,))
    result["clubs"] = [r[0] for r in cur.fetchall()]
    return result


def business(state):
    result = copy.deepcopy(state)
    for row in result["scraping_sources"]:
        if row["id"] == SOURCE_ID:
            row.pop("updated_at", None)
    return result


def expected_after(before):
    sources = before["scraping_sources"]
    if len(before["clubs"]) != 1 or {r["id"] for r in sources} != {SOURCE_ID}:
        raise ValueError("Reviewed venue/source cohort changed")
    source = sources[0]
    identity = dict(
        id=SOURCE_ID,
        club_id=CLUB_ID,
        source_url=URL,
        scraper_key="seatengine_classic",
        platform="seatengine",
        seatengine_id=324,
        enabled=True,
    )
    if any(source.get(k) != v for k, v in identity.items()):
        raise ValueError("Reviewed source identity changed")
    result = copy.deepcopy(before)
    result["scraping_sources"][0]["enabled"] = False
    return result


def build_plan(cur, reviewed_source):
    lock_schema(cur)
    before = snapshot(cur)
    if before["scraping_sources"] != [reviewed_source]:
        raise ValueError("Source differs from reviewed before-image")
    after = expected_after(before)
    return dict(
        task_id=4142,
        source_id=SOURCE_ID,
        expected_source=reviewed_source,
        before_hash=digest(before),
        after_business_hash=digest(business(after)),
    )


def validate_plan(plan):
    if plan.get("task_id") != 4142 or plan.get("source_id") != SOURCE_ID:
        raise ValueError("Exact TASK-4142 reviewed plan required")


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    before = snapshot(cur)
    if digest(business(before)) == plan["after_business_hash"]:
        return dict(already_applied=True, before=before, after=before)
    if digest(before) != plan["before_hash"] or before["scraping_sources"] != [plan["expected_source"]]:
        raise ValueError("Exact before-image drift")
    expected = expected_after(before)
    if digest(business(expected)) != plan["after_business_hash"]:
        raise ValueError("Reviewed after-image mismatch")
    backup = dict(task_id=4142, plan_hash=digest(plan), schema=schema, before=before, before_hash=digest(before))
    if backup_path:
        save_backup(backup_path, backup)
    cur.execute(
        "UPDATE scraping_sources SET enabled=false WHERE id=%s AND club_id=%s AND enabled=true", (SOURCE_ID, CLUB_ID)
    )
    if cur.rowcount != 1:
        raise ValueError("Reviewed source disappeared")
    after = snapshot(cur)
    if business(after) != business(expected):
        raise ValueError("Source-only preservation failed")
    backup.update(after=after, after_hash=digest(after), already_applied=False)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", backup)
    return backup


def restore(cur, plan, backup):
    validate_plan(plan)
    if backup.get("task_id") != 4142 or backup.get("plan_hash") != digest(plan):
        raise ValueError("Recovery does not match reviewed plan")
    if lock_schema(cur) != backup["schema"]:
        raise ValueError("Schema changed since backup")
    if any(digest(backup[k]) != backup[k + "_hash"] for k in ("before", "after")):
        raise ValueError("Recovery checksum mismatch")
    if backup["before_hash"] != plan["before_hash"] or digest(business(backup["after"])) != plan["after_business_hash"]:
        raise ValueError("Recovery differs from plan")
    if business(expected_after(backup["before"])) != business(backup["after"]):
        raise ValueError("Recovery contains unreviewed changes")
    current = snapshot(cur)
    if business(current) == business(backup["before"]):
        return False
    if current != backup["after"]:
        raise ValueError("Affected after-state drift; refusing restore")
    cur.execute(
        "UPDATE scraping_sources SET enabled=true WHERE id=%s AND club_id=%s AND enabled=false", (SOURCE_ID, CLUB_ID)
    )
    if cur.rowcount != 1 or business(snapshot(cur)) != business(backup["before"]):
        raise ValueError("Restore failed exact business-state preservation")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--restore", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private --backup")
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    from laughtrack.adapters.db import get_transaction

    plan = json.loads(args.plan.read_text())
    with get_transaction() as conn:
        with conn.cursor() as cur:
            if args.restore:
                print(json.dumps(dict(restored=restore(cur, plan, json.loads(args.restore.read_text())))))
            else:
                result = repair(cur, plan, args.backup if args.apply else None)
                print(
                    json.dumps(
                        dict(
                            already_applied=result["already_applied"],
                            counts={k: len(v) for k, v in result["after"].items()},
                        )
                    )
                )
        if not args.apply and not args.restore:
            conn.rollback()
            print("PLAN: rolled back")
    if args.apply or args.restore:
        print("COMMITTED: reviewed source enabled state")


if __name__ == "__main__":
    main()
