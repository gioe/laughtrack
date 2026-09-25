#!/usr/bin/env python3
"""Guarded Port Comedy showtime repair (TASK-4050).

Background
----------
Stale SeeTickets rows contain invented local-midnight showtimes. The reviewed
venue calendar supplies exact times for retained event IDs; only explicitly
reviewed unsupported future IDs may be retired.

What this script does
---------------------
Updates dates in place, retires enumerated rows, and selects the venue calendar
in source metadata. Retains click IDs through ON DELETE SET NULL. Private backup
contains all affected relationships and exact reversible before/after states.
No history is deleted. Default dry run rolls back; restore refuses any drift.

Usage
-----
From apps/scraper with PYTHONPATH=src:.:
  .venv/bin/python scripts/archive/repair_port_showtimes_2026_09_24.py --dry-run
  ... --apply --backup /private/path/task4050-recovery.json
  ... --restore /private/path/task4050-recovery.json
Backups contain user data and must never be committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from psycopg2 import sql

CLUB_ID = 11482
SOURCE_ID = 7054
CALENDAR_URL = "https://portcomedy.com/calendar/"
PLAN_PATH = Path(__file__).resolve().parents[2] / "docs/audits/2026-09-24-port/reviewed-plan.json"
REVIEWED_PLAN = json.loads(PLAN_PATH.read_text())
CHILDREN = (
    "tickets",
    "lineup_items",
    "tagged_shows",
    "saved_shows",
    "sent_notifications",
    "discovery_show_feature_snapshots",
    "ticket_purchase_click_events",
)
TABLES = ["scraping_sources", "shows", *CHILDREN]


def plan_hash():
    return hashlib.sha256(json.dumps(REVIEWED_PLAN, sort_keys=True).encode()).hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Reviewed timestamps must include timezone")
    return result


def schema(cur):
    cur.execute("""SELECT c.conrelid::regclass::text,a.attname,c.confdeltype
        FROM pg_constraint c JOIN LATERAL unnest(c.conkey) k(attnum) ON true
        JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum
        WHERE c.confrelid='shows'::regclass AND c.contype='f'""")
    actual = {(r[0].split(".")[-1].strip('"'), r[1], r[2]) for r in cur.fetchall()}
    expected = {(t, "show_id", "n" if t == "ticket_purchase_click_events" else "c") for t in CHILDREN}
    if actual != expected:
        raise ValueError("Show foreign keys changed; review recovery coverage")
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
            raise ValueError(f"{table} has no primary key for recovery")
        cur.execute(
            "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s::regclass ORDER BY conname",
            (table,),
        )
        constraints = cur.fetchall()
        cur.execute(
            "SELECT indexrelid::regclass::text,pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid=%s::regclass ORDER BY indexrelid::regclass::text",
            (table,),
        )
        result[table] = {"columns": columns, "primary": primary, "constraints": constraints, "indexes": cur.fetchall()}
    return json.loads(json.dumps(result))


def lock_and_validate_schema(cur):
    cur.execute("SET LOCAL lock_timeout='5s'; SET LOCAL TIME ZONE 'UTC'")
    cur.execute(
        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(sql.SQL(",").join(map(sql.Identifier, TABLES)))
    )
    return schema(cur)


def snapshot(cur, click_ids=()):
    cur.execute("SELECT id FROM shows WHERE club_id=%s", (CLUB_ID,))
    show_ids = sorted({r[0] for r in cur.fetchall()} | {int(k) for k in REVIEWED_PLAN.get("expected_shows", {})})
    result = {}
    for table in TABLES:
        if table == "scraping_sources":
            where, args = sql.SQL("club_id=%s OR id=%s"), (CLUB_ID, SOURCE_ID)
        elif table == "shows":
            where, args = sql.SQL("club_id=%s OR id=ANY(%s)"), (CLUB_ID, show_ids)
        else:
            where, args = sql.SQL("show_id=ANY(%s)"), (show_ids,)
            if table == "ticket_purchase_click_events":
                where += sql.SQL(" OR id=ANY(%s) OR club_id=%s")
                args += (list(click_ids), CLUB_ID)
        cur.execute(sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}").format(sql.Identifier(table), where), args)
        result[table] = sorted([r[0] for r in cur.fetchall()], key=lambda r: json.dumps(r, sort_keys=True))
    return result


def validate(cur, state):
    plan = REVIEWED_PLAN
    if not plan or not plan.get("expected_shows"):
        raise ValueError("Reviewed evidence plan is not populated")
    expected = {int(k): v for k, v in plan["expected_shows"].items()}
    updates = {int(k): v for k, v in plan["updates"].items()}
    retire = set(plan["retire_ids"])
    if set(updates) & retire or not (set(updates) | retire) <= set(expected):
        raise ValueError("Reviewed dispositions must reference unique expected show IDs")
    problems = []
    sources = {r["id"]: r for r in state["scraping_sources"]}
    if set(sources) != set(plan.get("expected_source_ids", [SOURCE_ID])):
        problems.append("Source cohort drift")
    source = sources.get(SOURCE_ID, {})
    marker = (source.get("metadata") or {}).get("task_4050_showtime_repair")
    applied = marker == plan_hash()
    if marker is not None and not applied:
        problems.append("Unknown repair marker")
    for key, value in plan["expected_source"].items():
        wanted = value
        if key == "metadata" and applied:
            wanted = dict(value or {}, calendar_url=CALENDAR_URL, task_4050_showtime_repair=plan_hash())
        if source.get(key) != wanted:
            problems.append(f"Source {key} drift")
    rows = {r["id"]: r for r in state["shows"]}
    cutoff = timestamp(plan["captured_at"])
    future = {r["id"] for r in rows.values() if r["club_id"] == CLUB_ID and timestamp(r["date"]) > cutoff}
    wanted_future = {i for i, r in expected.items() if timestamp(r["date"]) > cutoff}
    if applied:
        wanted_future -= retire
        wanted_future |= {i for i, v in updates.items() if timestamp(v) > cutoff}
    if set(rows) != set(expected) - (retire if applied else set()):
        problems.append("Exact show cohort drift")
    if future != wanted_future:
        problems.append("Future cohort drift")
    for ident, original in expected.items():
        before_date = timestamp(original["date"])
        local = before_date.astimezone(ZoneInfo("America/New_York"))
        if ident in set(updates) | retire and (
            original.get("last_scraped_by") != "seetickets_whitelabel"
            or (local.hour, local.minute, local.second, local.microsecond) != (0, 0, 0, 0)
        ):
            problems.append(f"Unreviewed original shape {ident}")
        if ident in retire and before_date <= cutoff:
            problems.append(f"Refusing to retire historical show {ident}")
        if applied and ident in retire:
            if ident in rows:
                problems.append(f"Retired show reappeared {ident}")
            continue
        row = rows.get(ident, {})
        if row.get("club_id") != CLUB_ID:
            problems.append(f"Show {ident} venue drift")
        for key, value in original.items():
            wanted = updates[ident] if applied and key == "date" and ident in updates else value
            actual = row.get(key)
            equal = (
                timestamp(actual) == timestamp(wanted)
                if key in {"date", "last_scraped_date"} and actual is not None and wanted is not None
                else actual == wanted
            )
            if not equal:
                problems.append(f"Show {ident} {key} drift")
    targets = set()
    for ident, new_date in updates.items():
        when = timestamp(new_date)
        old = expected[ident]
        if when <= cutoff:
            problems.append(f"New showtime is not future: {ident}")
        key = (when, old.get("room"))
        if key in targets:
            problems.append(f"Reviewed destination collision {ident}")
        targets.add(key)
        for row in rows.values():
            if (
                row["id"] != ident
                and row["id"] not in retire
                and row["club_id"] == CLUB_ID
                and timestamp(row["date"]) == when
                and row.get("room") == old.get("room")
            ):
                problems.append(f"Live destination collision {ident}")
    if problems:
        raise ValueError("; ".join(problems))
    return applied


def repair(cur, before):
    if validate(cur, before):
        return
    for ident, value in REVIEWED_PLAN["updates"].items():
        cur.execute("UPDATE shows SET date=%s WHERE id=%s", (value, int(ident)))
    cur.execute("DELETE FROM shows WHERE id=ANY(%s)", (REVIEWED_PLAN["retire_ids"],))
    cur.execute(
        "UPDATE scraping_sources SET metadata=COALESCE(metadata,'{}'::jsonb)||%s::jsonb WHERE id=%s",
        (json.dumps({"calendar_url": CALENDAR_URL, "task_4050_showtime_repair": plan_hash()}), SOURCE_ID),
    )


def restore(cur, backup):
    if backup.get("task_id") != 4050 or backup.get("plan_hash") != plan_hash():
        raise ValueError("Recovery file does not match reviewed TASK-4050 plan")
    live_schema = schema(cur)
    if live_schema != backup["schema"]:
        raise ValueError("Schema changed since backup")
    click_ids = backup["click_ids"]
    live = snapshot(cur, click_ids)
    if live == backup["before"]:
        return
    if live != backup["after"]:
        raise ValueError("Affected rows changed after repair; refusing restore")

    def index(table, rows):
        keys = live_schema[table]["primary"]
        return {tuple(row[k] for k in keys): row for row in rows}

    before = {t: index(t, backup["before"][t]) for t in TABLES}
    after = {t: index(t, backup["after"][t]) for t in TABLES}
    # Remove only new rows first, children before parents; never delete clubs.
    for table in reversed(TABLES):
        keys = live_schema[table]["primary"]
        for ident in after[table].keys() - before[table].keys():
            where = sql.SQL(" AND ").join(sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(k)) for k in keys)
            cur.execute(sql.SQL("DELETE FROM {} WHERE {}").format(sql.Identifier(table), where), ident)
    # Restore removed parents before child reassignments. Existing rows update
    # from full record snapshots, retaining IDs and original business fields.
    for table in TABLES:
        for ident, row in before[table].items():
            if ident not in after[table]:
                cur.execute(
                    sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s::jsonb)").format(
                        sql.Identifier(table), sql.Identifier(table)
                    ),
                    (json.dumps(row),),
                )
            elif row != after[table][ident]:
                keys = live_schema[table]["primary"]
                cols = [c for c in row if c not in keys]
                sets = sql.SQL(",").join(sql.SQL("{}=r.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in cols)
                where = sql.SQL(" AND ").join(
                    sql.SQL("t.{} IS NOT DISTINCT FROM r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys
                )
                cur.execute(
                    sql.SQL("UPDATE {} t SET {} FROM jsonb_populate_record(NULL::{},%s::jsonb) r WHERE {}").format(
                        sql.Identifier(table), sets, sql.Identifier(table), where
                    ),
                    (json.dumps(row),),
                )
    if snapshot(cur, click_ids) != backup["before"]:
        raise ValueError("Restore did not reproduce exact before-state")


def save_backup(path, payload):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser(description="Guarded Port Comedy showtime repair")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--restore", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private --backup file")
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    from laughtrack.adapters.db import get_transaction

    with get_transaction() as conn:
        with conn.cursor() as cur:
            actual_schema = lock_and_validate_schema(cur)
            backup = json.loads(args.restore.read_text()) if args.restore else None
            before = snapshot(cur, backup["click_ids"] if backup else ())
            click_ids = [r["id"] for r in before["ticket_purchase_click_events"]]
            if backup:
                restore(cur, backup)
            else:
                repair(cur, before)
            after = snapshot(cur, click_ids)
            if not backup:
                validate(cur, after)
            label = "PLAN" if not args.apply and not args.restore else "APPLY"
            print(label + " BEFORE " + json.dumps({t: len(v) for t, v in before.items()}, sort_keys=True))
            print(label + " AFTER " + json.dumps({t: len(v) for t, v in after.items()}, sort_keys=True))
            if args.apply:
                save_backup(
                    args.backup,
                    {
                        "task_id": 4050,
                        "plan_hash": plan_hash(),
                        "schema": actual_schema,
                        "click_ids": click_ids,
                        "before": before,
                        "after": after,
                    },
                )
            elif not args.restore:
                conn.rollback()
                print("DRY RUN: rolled back")
    if args.apply or args.restore:
        print("Transaction committed")


if __name__ == "__main__":
    main()
