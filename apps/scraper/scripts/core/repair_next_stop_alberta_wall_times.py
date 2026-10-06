#!/usr/bin/env python3
"""Reconcile reviewed Alberta Next Stop Comedy instants (TASK-4119).

Background: obsolete winter offsets left wrong instants and duplicate event rows.
What this script does: applies an exact evidence manifest, preserves canonical show
IDs, moves all child references, and records the plan hash in durable private recovery files. Organizer, show
and venue rows have no metadata column, so no artificial source row is created. Unreviewed child conflicts fail closed. Private recovery
files include every affected field and must never be committed.
Usage: PYTHONPATH=src:. .venv/bin/python scripts/core/repair_next_stop_alberta_wall_times.py
  --plan reviewed-plan.json [--dry-run]
  --plan reviewed-plan.json --apply --backup /private/path/recovery.json
  --plan reviewed-plan.json --restore /private/path/recovery.json.after.json
Default dry-run rolls back. Recovery refuses changed schema or affected state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from psycopg2 import sql
from scripts.core.repair_annoyance_identity import CHILDREN, same_value, save_backup
from scripts.core.repair_seatengine_organizer_venues import merge_show

TABLES = ("clubs", "production_companies", "shows", *CHILDREN)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Reviewed timestamps must include timezone")
    return result


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
    expected = {(t, "show_id", "n" if t == "ticket_purchase_click_events" else "c") for t in CHILDREN}
    if actual != expected:
        raise ValueError("Show foreign keys changed; review recovery coverage")
    cur.execute(
        "SELECT conrelid::regclass::text FROM pg_constraint WHERE contype='f' AND confrelid=ANY(%s::regclass[])",
        (list(CHILDREN),),
    )
    if cur.fetchall():
        raise ValueError("Child inbound references require review before merging")
    result = {}
    for table in TABLES:
        cur.execute(
            "SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum",
            (table,),
        )
        columns = cur.fetchall()
        cur.execute(
            "SELECT a.attname FROM pg_index i JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,ord) ON true JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum WHERE i.indrelid=%s::regclass AND i.indisprimary ORDER BY k.ord",
            (table,),
        )
        primary = [r[0] for r in cur.fetchall()]
        if not primary:
            raise ValueError(f"{table} has no primary key")
        cur.execute(
            "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s::regclass ORDER BY conname",
            (table,),
        )
        constraints = cur.fetchall()
        cur.execute(
            "SELECT pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid=%s::regclass ORDER BY indexrelid::regclass::text",
            (table,),
        )
        result[table] = dict(columns=columns, primary=primary, constraints=constraints, indexes=cur.fetchall())
    return json.loads(json.dumps(result))


def snapshot(cur, plan):
    ids = list(map(int, plan["expected_shows"]))
    clubs = plan["cohort_club_ids"]
    # Include all venue destinations, even events from a different scraper, so a
    # physical slot collision can never disappear behind a source URL filter.
    cur.execute(
        "SELECT id FROM shows WHERE club_id=ANY(%s) AND date>%s OR id=ANY(%s)", (clubs, plan["captured_at"], ids)
    )
    ids = sorted(set(ids) | {r[0] for r in cur.fetchall()})
    result = {}
    for table in TABLES:
        column, values = (
            ("id", clubs)
            if table == "clubs"
            else (
                ("id", [plan["organizer_id"]])
                if table == "production_companies"
                else ("id", ids) if table == "shows" else ("show_id", ids)
            )
        )
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}=ANY(%s)").format(
                sql.Identifier(table), sql.Identifier(column)
            ),
            (values,),
        )
        result[table] = sorted((r[0] for r in cur.fetchall()), key=lambda r: json.dumps(r, sort_keys=True))
    return result


def validate_plan(plan):
    if plan.get("task_id") != 4119 or not plan.get("expected_shows") or not plan.get("groups"):
        raise ValueError("Expected populated TASK-4119 evidence plan")
    expected = {int(k): v for k, v in plan["expected_shows"].items()}
    seen = set()
    for group in plan["groups"]:
        ids = [group["canonical_id"], *group["duplicate_ids"]]
        if len(ids) != len(set(ids)) or seen.intersection(ids) or not set(ids) <= expected.keys():
            raise ValueError("Repair groups must be disjoint reviewed IDs")
        seen.update(ids)
        canonical = expected[group["canonical_id"]]
        if not {"date", "club_id", "show_page_url", "room"} <= canonical.keys():
            raise ValueError("Missing show identity guards")
        if canonical["club_id"] not in plan["cohort_club_ids"] or not canonical["show_page_url"].startswith(
            "https://www.nextstopcomedy.com/events/"
        ):
            raise ValueError("Unexpected event identity")
        for ident in ids:
            row = expected[ident]
            if any(row.get(k) != canonical.get(k) for k in ("club_id", "show_page_url", "room")):
                raise ValueError("Merge crosses venue/event/room identity")
            if timestamp(row["date"]) <= timestamp(plan["captured_at"]):
                raise ValueError("Refusing to alter history")
        if timestamp(group["target_date"]) <= timestamp(plan["captured_at"]):
            raise ValueError("Target date is historical")


def assert_fields(actual, wanted, label, problems):
    if actual is None or any(not same_value(k, actual.get(k), v) for k, v in wanted.items()):
        problems.append(f"{label} before/after image drift")


def validate(state, plan):
    validate_plan(plan)
    problems = []
    organizers = {r["id"]: r for r in state["production_companies"]}
    assert_fields(organizers.get(plan["organizer_id"]), plan["expected_organizer"], "Organizer", problems)
    live_shows = {r["id"]: r for r in state["shows"]}
    applied = all(
        g["canonical_id"] in live_shows
        and timestamp(live_shows[g["canonical_id"]]["date"]) == timestamp(g["target_date"])
        and not set(g["duplicate_ids"]).intersection(live_shows)
        for g in plan["groups"]
    )
    clubs = {r["id"]: r for r in state["clubs"]}
    for ident, expected in plan["expected_clubs"].items():
        assert_fields(clubs.get(int(ident)), expected, f"Venue {ident}", problems)
    shows = {r["id"]: r for r in state["shows"]}
    expected = {int(k): dict(v) for k, v in plan["expected_shows"].items()}
    retired = {i for g in plan["groups"] for i in g["duplicate_ids"]}
    if applied:
        for group in plan["groups"]:
            expected[group["canonical_id"]]["date"] = group["target_date"]
        for ident in retired:
            expected.pop(ident)
    if shows.keys() != expected.keys():
        problems.append("Exact show cohort drift")
    for ident, wanted in expected.items():
        assert_fields(shows.get(ident), wanted, f"Show {ident}", problems)
    destinations = set()
    for group in plan["groups"]:
        canonical = expected[group["canonical_id"]]
        target = timestamp(group["target_date"])
        key = (canonical["club_id"], target, canonical["room"])
        if key in destinations:
            problems.append("Reviewed destination collision")
        destinations.add(key)
        for row in shows.values():
            if (
                row["id"] not in retired | {group["canonical_id"]}
                and (row["club_id"], timestamp(row["date"]), row.get("room")) == key
            ):
                problems.append("Live destination collision")
    if problems:
        raise ValueError("; ".join(problems))
    return applied


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    before = snapshot(cur, plan)
    if validate(before, plan):
        return dict(already_applied=True, before=before, after=before)
    backup = dict(
        task_id=4119, plan=plan, plan_hash=digest(plan), schema=schema, before=before, before_hash=digest(before)
    )
    if backup_path:
        save_backup(backup_path, backup)
    for group in plan["groups"]:
        for duplicate in group["duplicate_ids"]:
            merge_show(cur, duplicate, group["canonical_id"])
        cur.execute("UPDATE shows SET date=%s WHERE id=%s", (group["target_date"], group["canonical_id"]))
        if cur.rowcount != 1:
            raise ValueError("Canonical show disappeared")
    after = snapshot(cur, plan)
    validate(after, plan)
    backup.update(after=after, after_hash=digest(after), already_applied=False)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", backup)
    return backup


def restore(cur, plan, backup):
    if backup.get("task_id") != 4119 or backup.get("plan_hash") != digest(plan):
        raise ValueError("Recovery file does not match reviewed plan")
    if lock_schema(cur) != backup["schema"]:
        raise ValueError("Schema changed since backup")
    if digest(backup["before"]) != backup["before_hash"] or digest(backup["after"]) != backup["after_hash"]:
        raise ValueError("Recovery image checksum mismatch")
    live = snapshot(cur, plan)
    if live == backup["before"]:
        return
    if live != backup["after"]:
        raise ValueError("Affected rows changed after repair; refusing restore")
    for table in reversed(TABLES):
        keys = backup["schema"][table]["primary"]
        old_ids = {tuple(r[k] for k in keys) for r in backup["before"][table]}
        new_ids = {tuple(r[k] for k in keys) for r in backup["after"][table]}
        for ident in new_ids - old_ids:
            where = sql.SQL(" AND ").join(sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(k)) for k in keys)
            cur.execute(sql.SQL("DELETE FROM {} WHERE {}").format(sql.Identifier(table), where), ident)
    for table in TABLES:
        keys = backup["schema"][table]["primary"]

        def index(rows):
            return {tuple(r[k] for k in keys): r for r in rows}

        old, new = index(backup["before"][table]), index(backup["after"][table])
        for ident, row in sorted(old.items(), key=lambda item: item[0] not in new):
            if ident not in new:
                cur.execute(
                    sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s::jsonb)").format(
                        sql.Identifier(table), sql.Identifier(table)
                    ),
                    (json.dumps(row),),
                )
            elif row != new[ident]:
                cols = [k for k in row if k not in keys]
                sets = sql.SQL(",").join(sql.SQL("{}=r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in cols)
                where = sql.SQL(" AND ").join(
                    sql.SQL("t.{} IS NOT DISTINCT FROM r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys
                )
                cur.execute(
                    sql.SQL("UPDATE {} t SET {} FROM jsonb_populate_record(NULL::{},%s::jsonb) r WHERE {}").format(
                        sql.Identifier(table), sets, sql.Identifier(table), where
                    ),
                    (json.dumps(row),),
                )
    if snapshot(cur, plan) != backup["before"]:
        raise ValueError("Restore did not reproduce exact original business state")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
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

    load_dotenv(ROOT / ".env")
    from laughtrack.adapters.db import get_transaction

    plan = json.loads(args.plan.read_text())
    with get_transaction() as connection:
        with connection.cursor() as cur:
            if args.restore:
                restore(cur, plan, json.loads(args.restore.read_text()))
            else:
                result = repair(cur, plan, args.backup if args.apply else None)
                label = "APPLY" if args.apply else "PLAN"
                for phase in ("before", "after"):
                    print(
                        label
                        + " "
                        + phase.upper()
                        + " "
                        + json.dumps({t: len(rows) for t, rows in result[phase].items()}, sort_keys=True)
                    )
                print(json.dumps({"already_applied": result["already_applied"]}))
        if not args.apply and not args.restore:
            connection.rollback()
            print("PLAN: rolled back")
    if args.apply or args.restore:
        print("Transaction committed")


if __name__ == "__main__":
    main()
