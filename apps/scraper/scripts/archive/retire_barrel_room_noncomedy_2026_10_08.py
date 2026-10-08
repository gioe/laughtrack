#!/usr/bin/env python3
"""TASK-4143: retire 36 native-verified musical shows, preserving history.

Operator approved existing cleanup: ticket/tag rows cascade; click records survive
with show_id=NULL. New protected references abort. Full before/after images cover
the entire venue, disabled source and all seven child tables, including detached
clicks. Usage: --plan reviewed-plan.json [--apply --backup /private/new.json].
Recovery: --plan reviewed-plan.json --restore /private/new.json.after.json.
Default dry-run rolls back. Private recovery contains user data; never commit it.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from psycopg2 import sql
from scripts.archive.disable_barrel_room_source_2026_10_08 import lock_schema as source_schema
from scripts.core.repair_annoyance_identity import CHILDREN, plan_hash as digest, save_backup
from scripts.core.repair_seatengine_organizer_venues import rows

AUDIT = ROOT / "docs/audits/2026-10-08-barrel-room-noncomedy"
REVIEW_DIGEST = "4a5e50d0e177c5def24735ce887789329933548c1a46c154ef14c42e91138a75"
CLICKS = "ticket_purchase_click_events"
PROTECTED = ("lineup_items", "saved_shows", "sent_notifications", "discovery_show_feature_snapshots")


def evidence():
    review = json.loads((AUDIT / "native-review.json").read_text())
    if digest(review) != REVIEW_DIGEST:
        raise ValueError("Native review changed")
    return review


def lock_schema(cur):
    schema = source_schema(cur)
    cur.execute(
        "SELECT conrelid::regclass::text FROM pg_constraint WHERE contype='f' AND confrelid=ANY(%s::regclass[])",
        (list(CHILDREN),),
    )
    if cur.fetchall():
        raise ValueError("Child inbound references require recovery review")
    return schema


def snapshot(cur):
    reviewed_ids = [r["id"] for r in evidence()["shows"]]
    cur.execute("SELECT id FROM shows WHERE club_id=88 OR id=ANY(%s)", (reviewed_ids,))
    ids = [r[0] for r in cur.fetchall()]
    state = dict(shows=rows(cur, "shows", "id", ids), clubs=rows(cur, "clubs", "id", [88]))
    cur.execute("SELECT to_jsonb(s) FROM scraping_sources s WHERE club_id=88 OR id=77")
    state["scraping_sources"] = sorted((r[0] for r in cur.fetchall()), key=lambda r: json.dumps(r, sort_keys=True))
    state.update({table: rows(cur, table, "show_id", ids) for table in CHILDREN})
    cur.execute("SELECT to_jsonb(c) FROM ticket_purchase_click_events c WHERE club_id=88 OR show_id=ANY(%s)", (ids,))
    state[CLICKS] = sorted((r[0] for r in cur.fetchall()), key=lambda r: json.dumps(r, sort_keys=True))
    return state


def expected_after(before):
    review = evidence()
    selected = {r["id"]: r for r in review["shows"]}
    ids = set(selected)
    if len(ids) != 36 or len(before["clubs"]) != 1:
        raise ValueError("Reviewed cohort changed")
    sources = before["scraping_sources"]
    if len(sources) != 1 or sources[0]["id"] != 77 or sources[0]["club_id"] != 88 or sources[0]["enabled"]:
        raise ValueError("Disabled source identity changed")
    actual = {r["id"]: r for r in before["shows"]}
    for ident, native in selected.items():
        row = actual.get(ident)
        if not row or row["club_id"] != 88 or row["is_cancelled"]:
            raise ValueError("Reviewed show identity changed")
        if any(row[k] != native[k] for k in ("name", "show_page_url")) or datetime.fromisoformat(
            row["date"]
        ) != datetime.fromisoformat(native["date"]):
            raise ValueError("Reviewed native occurrence changed")
    if any(r["show_id"] in ids for t in PROTECTED for r in before[t]):
        raise ValueError("Protected reference on retiring show")
    if any(r["club_id"] != 88 for r in before[CLICKS]):
        raise ValueError("Click venue mismatch; review detached-click coverage")
    result = copy.deepcopy(before)
    result["shows"] = [r for r in result["shows"] if r["id"] not in ids]
    for table in ("tickets", "tagged_shows"):
        result[table] = [r for r in result[table] if r["show_id"] not in ids]
    for row in result[CLICKS]:
        if row["show_id"] in ids:
            row["show_id"] = None
    result["clubs"][0]["total_shows"] = len(result["shows"])
    return {t: sorted(v, key=lambda r: json.dumps(r, sort_keys=True)) for t, v in result.items()}


def build_plan(cur):
    schema = lock_schema(cur)
    before = snapshot(cur)
    after = expected_after(before)
    return dict(
        task_id=4143,
        review_digest=REVIEW_DIGEST,
        schema_hash=digest(schema),
        before_hash=digest(before),
        after_hash=digest(after),
        before_counts={t: len(v) for t, v in before.items()},
        after_counts={t: len(v) for t, v in after.items()},
    )


def validate_plan(cur, plan):
    if plan.get("task_id") != 4143 or plan.get("review_digest") != REVIEW_DIGEST:
        raise ValueError("Exact TASK-4143 reviewed plan required")
    schema = lock_schema(cur)
    if digest(schema) != plan["schema_hash"]:
        raise ValueError("Schema changed since plan")
    return schema


def repair(cur, plan, backup_path=None):
    schema = validate_plan(cur, plan)
    before = snapshot(cur)
    if digest(before) == plan["after_hash"]:
        return dict(already_applied=True, before=before, after=before)
    if digest(before) != plan["before_hash"]:
        raise ValueError("Exact before-image drift")
    expected = expected_after(before)
    if digest(expected) != plan["after_hash"]:
        raise ValueError("Reviewed after-image mismatch")
    # A delayed first apply may not delete an occurrence that has since become history.
    ids = [r["id"] for r in evidence()["shows"]]
    cur.execute("SELECT id FROM shows WHERE id=ANY(%s) AND date<=clock_timestamp()", (ids,))
    if cur.fetchall():
        raise ValueError("Reviewed occurrence is no longer future")
    backup = dict(task_id=4143, plan_hash=digest(plan), schema=schema, before=before, before_hash=digest(before))
    if backup_path:
        save_backup(backup_path, backup)
    cur.execute("DELETE FROM shows WHERE club_id=88 AND id=ANY(%s) RETURNING id", (ids,))
    if {r[0] for r in cur.fetchall()} != set(ids):
        raise ValueError("Deletion cohort changed")
    cur.execute("UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=88) WHERE id=88")
    after = snapshot(cur)
    if after != expected:
        raise ValueError("Cleanup preservation failed")
    backup.update(after=after, after_hash=digest(after), already_applied=False)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", backup)
    return backup


def restore(cur, plan, backup):
    schema = validate_plan(cur, plan)
    if backup.get("task_id") != 4143 or backup.get("plan_hash") != digest(plan) or backup.get("schema") != schema:
        raise ValueError("Recovery does not match plan/schema")
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
    ids = {r["id"] for r in evidence()["shows"]}
    for table in ("shows", "tickets", "tagged_shows"):
        for row in backup["before"][table]:
            if row["id" if table == "shows" else "show_id"] in ids:
                cur.execute(
                    sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s::jsonb)").format(
                        sql.Identifier(table), sql.Identifier(table)
                    ),
                    (json.dumps(row),),
                )
    for row in backup["before"][CLICKS]:
        if row["show_id"] in ids:
            cur.execute(
                "UPDATE ticket_purchase_click_events SET show_id=%s WHERE id=%s AND show_id IS NULL",
                (row["show_id"], row["id"]),
            )
            if cur.rowcount != 1:
                raise ValueError("Click restore count changed")
    cur.execute("UPDATE clubs SET total_shows=%s WHERE id=88", (backup["before"]["clubs"][0]["total_shows"],))
    if snapshot(cur) != backup["before"]:
        raise ValueError("Recovery failed exact preservation")
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
        parser.error("--apply requires a fresh private --backup")
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
                            counts={t: len(v) for t, v in result["after"].items()},
                        )
                    )
                )
        if not args.apply and not args.restore:
            conn.rollback()
            print("PLAN: rolled back")
    if args.apply or args.restore:
        print("COMMITTED: reviewed Barrel Room cleanup/recovery")


if __name__ == "__main__":
    main()
