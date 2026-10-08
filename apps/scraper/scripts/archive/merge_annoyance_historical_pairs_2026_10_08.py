#!/usr/bin/env python3
"""Merge two source-reviewed historical Annoyance performance pairs (TASK-4136).

Background: historical ThunderTix records identify two duplicated performances.
What this does: retains the reviewed show IDs and migrates all seven relationship
tables. God Lens, retained show identities, venue and source rows remain unchanged;
ticket triggers refresh the retained shows' derived price and availability caches.
Usage: --plan reviewed.json [--apply --backup /private/new.json]; or
--plan reviewed.json --restore /private/new.json.after.json.
Default dry-run rolls back. Apply durably writes a private before-image BEFORE
mutations; recovery requires an exact after-state. Never commit recovery files.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2 import sql

from scripts.core.repair_annoyance_identity import CHILDREN, save_backup, ticket_identity
from scripts.core.repair_next_stop_alberta_wall_times import lock_schema as base_lock_schema
from scripts.core.repair_seatengine_organizer_venues import CHILD_KEYS, digest, merge_show, rows

PAIRS = (
    (3769502, 7451272, 188918, 3256449, "2026-09-20T01:00:00+00:00"),
    (847662, 1371908, 263284, 3249429, "2026-05-24T23:30:00+00:00"),
)
HELD_IDS = (1024865, 927780)
SHOW_IDS = tuple(i for pair in PAIRS for i in pair[:2]) + HELD_IDS
TABLES = ("clubs", "scraping_sources", "shows", *CHILDREN)
TICKET_FILLS = [
    dict(from_id=4225195, to_id=8491061, price=15.0),
    dict(from_id=782156, to_id=1320025, price=0.0),
]


def ordered(items):
    return sorted(items, key=lambda row: json.dumps(row, sort_keys=True))


def lock_schema(cur):
    schema = base_lock_schema(cur)
    cur.execute("LOCK TABLE scraping_sources IN SHARE ROW EXCLUSIVE MODE")
    cur.execute("""SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute
        WHERE attrelid='scraping_sources'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum""")
    columns = cur.fetchall()
    cur.execute("""SELECT a.attname FROM pg_index i
        JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,ord) ON true
        JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum
        WHERE i.indrelid='scraping_sources'::regclass AND i.indisprimary ORDER BY k.ord""")
    primary = [r[0] for r in cur.fetchall()]
    cur.execute("""SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conrelid='scraping_sources'::regclass ORDER BY conname""")
    constraints = cur.fetchall()
    cur.execute("""SELECT pg_get_indexdef(indexrelid) FROM pg_index
        WHERE indrelid='scraping_sources'::regclass ORDER BY indexrelid::regclass::text""")
    schema["scraping_sources"] = dict(columns=columns, primary=primary, constraints=constraints, indexes=cur.fetchall())
    for table in TABLES:
        cur.execute(
            """SELECT t.tgname,t.tgenabled,pg_get_triggerdef(t.oid),pg_get_functiondef(p.oid)
            FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
            WHERE t.tgrelid=%s::regclass AND NOT t.tgisinternal ORDER BY t.tgname""",
            (table,),
        )
        schema[table]["triggers"] = cur.fetchall()
    # PL/pgSQL function calls are not represented in pg_depend. Include the two
    # helpers called by the ticket trigger functions explicitly, not just the
    # directly attached trigger bodies, so changed cache semantics fail closed.
    cur.execute("""SELECT p.proname,pg_get_functiondef(p.oid) FROM pg_proc p
        WHERE p.proname IN ('refresh_show_min_price','refresh_show_tickets_sold_out')
          AND p.pronamespace IN (SELECT f.pronamespace FROM pg_trigger t
              JOIN pg_proc f ON f.oid=t.tgfoid WHERE t.tgrelid='tickets'::regclass AND NOT t.tgisinternal)
        ORDER BY p.proname,p.oid::regprocedure::text""")
    schema["ticket_cache_helpers"] = cur.fetchall()
    if len(schema["ticket_cache_helpers"]) != 2:
        raise ValueError("Reviewed ticket cache helpers missing or ambiguous")
    return json.loads(json.dumps(schema))


def snapshot(cur):
    cur.execute("SET LOCAL TIME ZONE 'UTC'")
    state = dict(
        shows=rows(cur, "shows", "id", SHOW_IDS),
        clubs=rows(cur, "clubs", "id", [183]),
        scraping_sources=rows(cur, "scraping_sources", "club_id", [183]),
    )
    state.update({table: rows(cur, table, "show_id", SHOW_IDS) for table in CHILDREN})
    return state


def validate_before(state):
    shows = {r["id"]: r for r in state["shows"]}
    if set(shows) != set(SHOW_IDS) or len(state["clubs"]) != 1 or not state["scraping_sources"]:
        raise ValueError("Exact six-show Annoyance cohort, venue and sources required")
    for old, new, event, performance, date in PAIRS:
        native = f"thundertix:theannoyance:{event}:{performance}"
        for ident in (old, new):
            row = shows[ident]
            if (
                row["club_id"] != 183
                or row["show_page_url"] != f"https://theannoyance.thundertix.com/events/{event}"
                or row.get("source_performance_id") is not None
            ):
                raise ValueError("Reviewed show identity changed")
            tickets = [r for r in state["tickets"] if r["show_id"] == ident]
            if not tickets or any(ticket_identity(r["purchase_url"]) != native for r in tickets):
                raise ValueError("Reviewed native ticket identity changed")
        if datetime.fromisoformat(shows[new]["date"]) != datetime.fromisoformat(date):
            raise ValueError("Survivor no longer matches source-proven date")
        if shows[old].get("room") != shows[new].get("room"):
            raise ValueError("Reviewed room identity changed")
    if any(shows[ident]["club_id"] != 183 for ident in HELD_IDS):
        raise ValueError("Held God Lens venue changed")
    tickets = {r["id"]: r for r in state["tickets"]}
    for fill, pair in zip(TICKET_FILLS, PAIRS):
        old, new = tickets.get(fill["from_id"]), tickets.get(fill["to_id"])
        if (
            not old
            or not new
            or old["show_id"] != pair[0]
            or new["show_id"] != pair[1]
            or old["price"] != fill["price"]
            or new["price"] is not None
            or any(v != new.get(k) for k, v in old.items() if k not in {"id", "show_id", "price"})
        ):
            raise ValueError("Reviewed null-price ticket coalescence changed")


def expected_after(before):
    result = copy.deepcopy(before)
    # These exact reviewed tickets differ only in a known legacy price versus an
    # unknown survivor price. Preserve the known value; do not infer a new price.
    tickets = {r["id"]: r for r in result["tickets"]}
    for fill in TICKET_FILLS:
        tickets[fill["to_id"]]["price"] = fill["price"]
    for old, new, *_ in PAIRS:
        for table in CHILDREN:
            keys = CHILD_KEYS.get(table)
            target = [r for r in result[table] if r["show_id"] == new]
            merged = []
            for row in result[table]:
                if row["show_id"] != old:
                    merged.append(row)
                    continue
                collision = next((r for r in target if keys and all(r.get(k) == row.get(k) for k in keys)), None)
                if collision:
                    if any(v != collision.get(k) for k, v in row.items() if k not in {"id", "show_id"}):
                        raise ValueError(f"Lossless merge conflict: {table}")
                else:
                    merged.append(dict(row, show_id=new))
            result[table] = ordered(merged)
        result["shows"] = [r for r in result["shows"] if r["id"] != old]
        survivor = next(r for r in result["shows"] if r["id"] == new)
        tickets = [r for r in result["tickets"] if r["show_id"] == new]
        positive_prices = [r["price"] for r in tickets if r["price"] is not None and r["price"] > 0]
        survivor["min_price"] = min(positive_prices, default=None)
        survivor["tickets_sold_out"] = bool(tickets) and all(r["sold_out"] for r in tickets)
    result["shows"] = ordered(result["shows"])
    return result


def build_plan(cur):
    schema = lock_schema(cur)
    before = snapshot(cur)
    validate_before(before)
    after = expected_after(before)
    return dict(
        task_id=4136,
        schema=schema,
        expected_shows=before["shows"],
        ticket_fills=copy.deepcopy(TICKET_FILLS),
        before_hash=digest(before),
        after_hash=digest(after),
    )


def repair(cur, plan, backup_path=None):
    if plan.get("task_id") != 4136 or plan.get("ticket_fills") != TICKET_FILLS:
        raise ValueError("TASK-4136 reviewed plan required")
    schema = lock_schema(cur)
    if schema != plan["schema"]:
        raise ValueError("Schema changed since reviewed plan")
    before = snapshot(cur)
    if digest(before) == plan["after_hash"]:
        return dict(already_applied=True, before=before, after=before)
    if digest(before) != plan["before_hash"] or before["shows"] != plan["expected_shows"]:
        raise ValueError("Exact before-image drift")
    validate_before(before)
    expected = expected_after(before)
    if digest(expected) != plan["after_hash"]:
        raise ValueError("Reviewed after-image mismatch")
    backup = dict(task_id=4136, plan_hash=digest(plan), schema=schema, before=before, before_hash=digest(before))
    if backup_path:
        save_backup(backup_path, backup)
    for fill in TICKET_FILLS:
        cur.execute("UPDATE tickets SET price=%s WHERE id=%s AND price IS NULL", (fill["price"], fill["to_id"]))
        if cur.rowcount != 1:
            raise ValueError("Reviewed null-price ticket disappeared")
    for old, new, *_ in PAIRS:
        merge_show(cur, old, new)
    after = snapshot(cur)
    if after != expected:
        raise ValueError("Relationship or held-row preservation failed")
    backup.update(after=after, after_hash=digest(after), already_applied=False)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", backup)
    return backup


def restore(cur, plan, backup):
    if backup.get("task_id") != 4136 or backup.get("plan_hash") != digest(plan):
        raise ValueError("Recovery does not match reviewed plan")
    if lock_schema(cur) != backup["schema"] or backup["schema"] != plan["schema"]:
        raise ValueError("Schema changed since backup")
    if any(
        digest(backup[k]) != backup[k + "_hash"] or backup[k + "_hash"] != plan[k + "_hash"]
        for k in ("before", "after")
    ):
        raise ValueError("Recovery checksum mismatch")
    current = snapshot(cur)
    if current == backup["before"]:
        return False
    if current != backup["after"]:
        raise ValueError("Affected after-state drift; refusing restore")
    # No new identities are created by this repair. Restore missing parents first,
    # then recreate coalesced children and repoint existing children by primary key.
    for table in TABLES:
        keys = backup["schema"][table]["primary"]
        old = {tuple(r[k] for k in keys): r for r in backup["before"][table]}
        new = {tuple(r[k] for k in keys): r for r in backup["after"][table]}
        # Composite relationship PKs move with show_id: remove the moved key before
        # recreating the old key, but retain pre-existing destination relationships.
        for ident in new.keys() - old.keys():
            where = sql.SQL(" AND ").join(sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(k)) for k in keys)
            cur.execute(sql.SQL("DELETE FROM {} WHERE {}").format(sql.Identifier(table), where), ident)
        for ident, row in old.items():
            if ident not in new:
                cur.execute(
                    sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s::jsonb)").format(
                        sql.Identifier(table), sql.Identifier(table)
                    ),
                    (json.dumps(row),),
                )
            elif row != new[ident]:
                columns = [k for k in row if k not in keys]
                assignments = sql.SQL(",").join(
                    sql.SQL("{}=r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in columns
                )
                where = sql.SQL(" AND ").join(
                    sql.SQL("t.{} IS NOT DISTINCT FROM r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys
                )
                cur.execute(
                    sql.SQL("UPDATE {} t SET {} FROM jsonb_populate_record(NULL::{},%s::jsonb) r WHERE {}").format(
                        sql.Identifier(table), assignments, sql.Identifier(table), where
                    ),
                    (json.dumps(row),),
                )
    if snapshot(cur) != backup["before"]:
        raise ValueError("Restore failed exact preservation")
    return True


def main():
    parser = argparse.ArgumentParser(description="Apply the reviewed TASK-4136 historical duplicate repair.")
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

    load_dotenv(_root / ".env")
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
                            before={k: len(v) for k, v in result["before"].items()},
                            after={k: len(v) for k, v in result["after"].items()},
                        )
                    )
                )
        if not args.apply and not args.restore:
            conn.rollback()
            print("DRY RUN: rolled back")
    if args.apply or args.restore:
        print("COMMITTED: reviewed Annoyance historical pair repair")


if __name__ == "__main__":
    main()
