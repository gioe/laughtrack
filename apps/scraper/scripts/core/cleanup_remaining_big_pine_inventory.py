#!/usr/bin/env python3
"""Clean up the freshly reviewed remaining Big Pine products.

Background: TASK-4111 deliberately held this inventory pending native evidence.
What this script does: delete exactly 36 reviewed products, preserving festival
identity, sources, targets and click records, with dependent-aware recovery.
Usage: --dry-run (default), --apply --backup /private/path/new.json, or
--restore /private/path/new.json.after.json. Recovery files contain private data.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2 import sql
from scripts.core.cleanup_big_pine_inventory import TABLES, CLICKS, lock_schema, snapshot as original_snapshot
from scripts.core.repair_annoyance_identity import CHILDREN, save_backup
from scripts.core.repair_seatengine_organizer_venues import digest, rows

AUDIT = _root / "docs/audits/2026-10-07-big-pine-remaining"
PLAN_PATH = AUDIT / "plan.json"
DECISIONS_HASH = "da5688ca4acdd731e2e2183871f299044e249cac063b7605188cc2ba2d4b36b4"
RETIRE_IDS = {
    522171,
    522172,
    522173,
    522174,
    522187,
    522188,
    522189,
    522190,
    1418265,
    1376604,
    1376607,
    1376608,
    1376609,
    522193,
    1376611,
    522194,
    1550284,
    1550285,
    1376613,
    1376614,
    1376615,
    1376616,
    1376617,
    1376618,
    1376619,
    1376620,
    522195,
    1376622,
    1376623,
    1376624,
    1376626,
    1376627,
    1376630,
    1376631,
    1376632,
    7773673,
}


def snapshot(cur, plan, click_ids=()):
    state = original_snapshot(cur, plan)
    cur.execute("SELECT id FROM ticket_purchase_click_events WHERE club_id=573")
    ids = (
        set(click_ids)
        | set(plan.get("click_ids", []))
        | {r[0] for r in cur.fetchall()}
        | {r["id"] for r in state[CLICKS]}
    )
    state[CLICKS] = rows(cur, CLICKS, "id", ids)
    return state


def expected_after(before):
    state = deepcopy(before)
    state["shows"] = [r for r in state["shows"] if r["id"] not in RETIRE_IDS]
    for table in CHILDREN:
        if table == CLICKS:
            for row in state[table]:
                if row["show_id"] in RETIRE_IDS:
                    row["show_id"] = None
        else:
            state[table] = [r for r in state[table] if r["show_id"] not in RETIRE_IDS]
    state["clubs"][0]["total_shows"] = len(state["shows"])
    return {t: sorted(v, key=lambda r: json.dumps(r, sort_keys=True)) for t, v in state.items()}


def validate_plan(plan):
    if (plan["task_id"], plan["club_id"], plan["source_id"]) != (4132, 573, 360):
        raise ValueError("Unexpected task/source identity")
    if set(plan["retire_ids"]) != RETIRE_IDS or len(plan["retire_ids"]) != 36:
        raise ValueError("Deletion cohort must be exactly the 36 reviewed IDs")
    decisions = json.loads((AUDIT / "decisions.json").read_text())
    if digest(decisions) != DECISIONS_HASH:
        raise ValueError("Reviewed native decisions changed")
    if set(plan["inventory_ids"]) != {r["show_id"] for r in decisions} or len(plan["inventory_ids"]) != 53:
        raise ValueError("Inventory must match the 53 reviewed occurrences")
    for key in ("before_hashes", "expected_counts", "after_hashes", "after_counts"):
        if set(plan[key]) != set(TABLES):
            raise ValueError("Missing dependency before-images")
    if len(plan["click_ids"]) != len(set(plan["click_ids"])):
        raise ValueError("Duplicate recorded click IDs")
    return decisions


def matches(state, hashes, counts):
    return all(len(state[t]) == counts[t] and digest(state[t]) == hashes[t] for t in TABLES)


def repair(cur, plan, backup_path=None):
    decisions = validate_plan(plan)
    schema = lock_schema(cur)
    before = snapshot(cur, plan)
    # Detached historical clicks require their recorded IDs for exact rerun checks.
    if matches(before, plan["after_hashes"], plan["after_counts"]):
        if {r["id"] for r in before["shows"]} != set(plan["inventory_ids"]) - RETIRE_IDS:
            raise ValueError("Reviewed after-image still includes products or lacks retained shows")
        return {"already_applied": True, "before": before, "after": before}
    for table in TABLES:
        if (
            len(before[table]) != plan["expected_counts"][table]
            or digest(before[table]) != plan["before_hashes"][table]
        ):
            raise ValueError(f"{table} before-image changed; re-review before applying")
    if {r["id"] for r in before["shows"]} != set(plan["inventory_ids"]):
        raise ValueError("Inventory cohort changed")
    source = next((r for r in before["scraping_sources"] if r["id"] == 360), None)
    if not source or source["club_id"] != 573 or not source["enabled"] or not before["clubs"][0]["visible"]:
        raise ValueError("Festival identity changed")
    reviewed = {r["show_id"]: r for r in decisions}
    for row in before["shows"]:
        if row["club_id"] != 573:
            raise ValueError("Show changed festival identity")
        if row["id"] not in RETIRE_IDS:
            continue
        evidence = reviewed[row["id"]]
        if (
            evidence["decision"] != "remove"
            or not evidence["date_matches"]
            or int(urlsplit(row["show_page_url"]).path.rstrip("/").split("/")[-1]) != evidence["native_id"]
            or row["show_page_url"] != evidence["show_page_url"]
            or row["name"] != evidence["stored_name"]
            or row["room"] != evidence["room"]
            or datetime.fromisoformat(row["date"]) != datetime.fromisoformat(evidence["stored_date"])
            or datetime.fromisoformat(row["date"]) != datetime.fromisoformat(evidence["native_date"])
        ):
            raise ValueError("Reviewed native occurrence identity changed")
    if not matches(expected_after(before), plan["after_hashes"], plan["after_counts"]):
        raise ValueError("Reviewed after-image does not match bounded cleanup")
    recovery = {
        "task_id": 4132,
        "plan": plan,
        "plan_hash": digest(plan),
        "schema": schema,
        "before": before,
        "before_hash": digest(before),
        "already_applied": False,
    }
    if backup_path:
        save_backup(backup_path, recovery)
    cur.execute("DELETE FROM shows WHERE club_id=573 AND id=ANY(%s) RETURNING id", (sorted(RETIRE_IDS),))
    if {r[0] for r in cur.fetchall()} != RETIRE_IDS:
        raise ValueError("Deletion count changed")
    cur.execute("UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=573) WHERE id=573")
    if cur.rowcount != 1:
        raise ValueError("Club count update changed")
    after = snapshot(cur, plan, [r["id"] for r in before[CLICKS]])
    if after != expected_after(before):
        raise ValueError("Unexpected after-image")
    recovery.update(after=after, after_hash=digest(after))
    if backup_path:
        save_backup(str(backup_path) + ".after.json", recovery)
    return recovery


def restore(cur, plan, backup):
    validate_plan(plan)
    if backup.get("task_id") != 4132 or backup.get("plan_hash") != digest(plan):
        raise ValueError("Recovery file does not match reviewed plan")
    if digest(lock_schema(cur)) != digest(backup["schema"]):
        raise ValueError("Schema changed since backup")
    if digest(backup["before"]) != backup["before_hash"] or digest(backup["after"]) != backup["after_hash"]:
        raise ValueError("Recovery image checksum mismatch")
    if not matches(backup["before"], plan["before_hashes"], plan["expected_counts"]) or not matches(
        backup["after"], plan["after_hashes"], plan["after_counts"]
    ):
        raise ValueError("Recovery images do not match reviewed plan")
    if backup["after"] != expected_after(backup["before"]):
        raise ValueError("Recovery images do not describe the bounded cleanup")
    click_ids = [r["id"] for r in backup["before"][CLICKS]]
    live = snapshot(cur, plan, click_ids)
    if live == backup["before"]:
        return
    if live != backup["after"]:
        raise ValueError("Affected rows changed after cleanup; refusing restore")
    for table in ("shows", *(t for t in CHILDREN if t != CLICKS)):
        for row in backup["before"][table]:
            if row["id" if table == "shows" else "show_id"] not in RETIRE_IDS:
                continue
            cur.execute(
                sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s::jsonb)").format(
                    sql.Identifier(table), sql.Identifier(table)
                ),
                (json.dumps(row),),
            )
    for row in backup["before"][CLICKS]:
        if row["show_id"] in RETIRE_IDS:
            cur.execute(
                "UPDATE ticket_purchase_click_events SET show_id=%s WHERE id=%s AND show_id IS NULL",
                (row["show_id"], row["id"]),
            )
            if cur.rowcount != 1:
                raise ValueError("Click restore count changed")
    cur.execute("UPDATE clubs SET total_shows=%s WHERE id=573", (backup["before"]["clubs"][0]["total_shows"],))
    if snapshot(cur, plan, click_ids) != backup["before"]:
        raise ValueError("Restore did not reproduce exact original state")


def main():
    parser = argparse.ArgumentParser(description="Guarded cleanup and recovery of 36 reviewed Big Pine products")
    parser.add_argument("--plan", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--restore", type=Path)
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
            if args.restore:
                restore(cur, plan, json.loads(args.restore.read_text()))
                print("RESTORED: exact original inventory and dependent records")
            else:
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


if __name__ == "__main__":
    main()
