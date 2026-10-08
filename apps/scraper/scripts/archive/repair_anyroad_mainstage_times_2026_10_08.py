#!/usr/bin/env python3
"""TASK-4140: correct two source-reviewed Mainstage times, preserving every ID.

Native experience 88719 changed November/December starts to 20:30 Eastern.
Only the two reviewed date fields may change. Full venue/cohort snapshots guard
relationships, collisions, repeat execution and rollback. Default dry-run rolls
back; apply requires a new private recovery file (never commit recovery files).
Usage: --plan reviewed-plan.json [--apply --backup /private/new.json]
Recovery: --plan reviewed-plan.json --restore /private/new.json.after.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.archive.repair_anyroad_blank_rooms_2026_10_08 import (
    digest,
    lock_schema,
    save_backup,
    snapshot,
    timestamp,
)

DATES = {3179528: "2026-11-22T01:30:00+00:00", 3179529: "2026-12-20T01:30:00+00:00"}
URL = "https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/riot-improv-mainstage-stories-to-scenes?lang=en-US"
ROOM = "18b Corinth Street, Boston, MA"


def expected_after(before):
    result = copy.deepcopy(before)
    shows = {r["id"]: r for r in result["shows"]}
    source = next((r for r in before["scraping_sources"] if r["id"] == 6820), None)
    if (
        not source
        or source["club_id"] != 10970
        or not source["enabled"]
        or (
            source["metadata"].get("plugin_id") != "rozziesquaretheater"
            or source["metadata"].get("anyroad_venue_routes", {}).get("producer_id") != 50
        )
    ):
        raise ValueError("Reviewed source identity changed")
    for ident, new_date in DATES.items():
        row = shows.get(ident)
        if not row or row["club_id"] != 10970 or row["room"] != ROOM or row["show_page_url"] != URL:
            raise ValueError("Reviewed show identity changed")
        old, target = timestamp(row["date"]), timestamp(new_date)
        if (target - old).total_seconds() != 1800:
            raise ValueError("Expected reviewed 20:00 to 20:30 correction")
        for other in shows.values():
            if other["id"] == ident:
                continue
            same_slot = (
                other["club_id"] == row["club_id"]
                and timestamp(other["date"]) == target
                and (other.get("room") or "") == ROOM
            )
            same_occurrence = (
                other["show_page_url"] == URL
                and timestamp(other["date"]).astimezone(ZoneInfo("America/New_York")).date()
                == target.astimezone(ZoneInfo("America/New_York")).date()
            )
            if same_slot or same_occurrence:
                raise ValueError("Live destination or native occurrence collision")
        row["date"] = new_date
    return result


def build_plan(cur):
    lock_schema(cur)
    before = snapshot(cur)
    after = expected_after(before)
    return dict(
        task_id=4140,
        dates={str(k): v for k, v in DATES.items()},
        expected_shows=[r for r in before["shows"] if r["id"] in DATES],
        before_hash=digest(before),
        after_hash=digest(after),
    )


def validate_plan(plan):
    if plan.get("task_id") != 4140 or plan.get("dates") != {str(k): v for k, v in DATES.items()}:
        raise ValueError("Exact TASK-4140 reviewed plan required")


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    before = snapshot(cur)
    if digest(before) == plan["after_hash"]:
        return dict(already_applied=True, before=before, after=before)
    if (
        digest(before) != plan["before_hash"]
        or [r for r in before["shows"] if r["id"] in DATES] != plan["expected_shows"]
    ):
        raise ValueError("Exact before-image drift")
    expected = expected_after(before)
    if digest(expected) != plan["after_hash"]:
        raise ValueError("Reviewed after-image mismatch")
    backup = dict(task_id=4140, plan_hash=digest(plan), schema=schema, before=before, before_hash=digest(before))
    if backup_path:
        save_backup(backup_path, backup)
    for ident, date in DATES.items():
        cur.execute("UPDATE shows SET date=%s WHERE id=%s", (date, ident))
        if cur.rowcount != 1:
            raise ValueError("Reviewed occurrence disappeared")
    after = snapshot(cur)
    if after != expected:
        raise ValueError("Relationship or unrelated inventory preservation failed")
    backup.update(after=after, after_hash=digest(after), already_applied=False)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", backup)
    return backup


def restore(cur, plan, backup):
    validate_plan(plan)
    if backup.get("task_id") != 4140 or backup.get("plan_hash") != digest(plan):
        raise ValueError("Recovery does not match reviewed plan")
    if lock_schema(cur) != backup["schema"]:
        raise ValueError("Schema changed since backup")
    if any(
        digest(backup[k]) != backup[k + "_hash"] or backup[k + "_hash"] != plan[k + "_hash"]
        for k in ("before", "after")
    ):
        raise ValueError("Recovery checksum mismatch")
    if expected_after(backup["before"]) != backup["after"]:
        raise ValueError("Recovery contains unreviewed changes")
    current = snapshot(cur)
    if current == backup["before"]:
        return False
    if current != backup["after"]:
        raise ValueError("Affected after-state drift; refusing restore")
    for row in backup["before"]["shows"]:
        if row["id"] in DATES:
            cur.execute("UPDATE shows SET date=%s WHERE id=%s", (row["date"], row["id"]))
    if snapshot(cur) != backup["before"]:
        raise ValueError("Restore failed exact preservation")
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
        parser.error("--apply requires a private --backup")
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
        print("COMMITTED: reviewed Mainstage time correction")


if __name__ == "__main__":
    main()
