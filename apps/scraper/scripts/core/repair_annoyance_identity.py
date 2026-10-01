#!/usr/bin/env python3
"""Backfill reviewed Annoyance performance identities without changing show IDs.

Background: simultaneous native ThunderTix performances cannot share the legacy
physical-slot key. This repair adopts only reviewed, ticket-verified identities.
What it does: updates source_performance_id and activates source metadata in one
transaction, preserving all shows and their seven relationship tables.
Usage: PYTHONPATH=src:. .venv/bin/python scripts/core/repair_annoyance_identity.py
Defaults to rollback dry-run. --apply requires a new private --backup path.
--restore restores business fields and relationships only when the full after-state
still matches. The source update trigger refreshes updated_at on apply and restore.
Backups contain private user data; never commit them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from psycopg2 import sql

PLAN_PATH = Path(__file__).resolve().parents[2] / "docs/audits/2026-09-30-annoyance-identity/reviewed-plan.json"
CHILDREN = (
    "tickets",
    "lineup_items",
    "tagged_shows",
    "saved_shows",
    "sent_notifications",
    "discovery_show_feature_snapshots",
    "ticket_purchase_click_events",
)
TABLES = ("scraping_sources", "shows", *CHILDREN)
MARKER = "task_4081_identity_repair"


def plan_hash(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


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
    result = {}
    for table in TABLES:
        cur.execute(
            "SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum",
            (table,),
        )
        columns = cur.fetchall()
        cur.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s::regclass ORDER BY conname", (table,)
        )
        constraints = cur.fetchall()
        cur.execute(
            "SELECT pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid=%s::regclass ORDER BY indexrelid::regclass::text",
            (table,),
        )
        result[table] = {"columns": columns, "constraints": constraints, "indexes": cur.fetchall()}
    if "source_performance_id" not in dict(result["shows"]["columns"]):
        raise ValueError("Apply the source performance schema migration first")
    return json.loads(json.dumps(result))


def snapshot(cur, plan):
    result = {}
    for table in TABLES:
        if table == "scraping_sources":
            where, args = sql.SQL("club_id=%s OR id=%s"), (plan["club_id"], plan["source_id"])
        elif table == "shows":
            where, args = sql.SQL("club_id=%s OR id=ANY(%s)"), (plan["club_id"], list(map(int, plan["expected_shows"])))
        else:
            where, args = sql.SQL("show_id IN (SELECT id FROM shows WHERE club_id=%s)"), (plan["club_id"],)
        cur.execute(sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}").format(sql.Identifier(table), where), args)
        result[table] = sorted((r[0] for r in cur.fetchall()), key=lambda value: json.dumps(value, sort_keys=True))
    return result


def ticket_identity(url):
    from laughtrack.core.entities.event.thundertix import ThunderTixPerformance

    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    events, performances = query.get("event_id", []), query.get("performance_id", [])
    if len(events) != 1 or len(performances) != 1 or parsed.path != "/orders/new":
        raise ValueError("Ticket lacks one unambiguous native performance identity")
    return ThunderTixPerformance(
        event_id=ThunderTixPerformance._positive_id(events[0]),
        performance_id=ThunderTixPerformance._positive_id(performances[0]),
        title="",
        start_dt="",
        ticket_url=url,
        show_page_url=url,
    ).source_identity()


def same_value(key, actual, expected):
    if key.endswith("_at") or key in {"date", "last_scraped_date"}:
        if actual is not None and expected is not None:
            return datetime.fromisoformat(actual.replace("Z", "+00:00")) == datetime.fromisoformat(
                expected.replace("Z", "+00:00")
            )
    return actual == expected


def validate(state, plan):
    expected = plan["expected_shows"]
    updates = plan["identity_updates"]
    if not expected or set(updates) != set(expected) or plan.get("retire_ids"):
        raise ValueError("Plan must contain only explicit identity updates")
    if len(set(updates.values())) != len(updates):
        raise ValueError("Reviewed identities are not unique")
    if plan["activation_metadata"] != {"source_performance_identity": True}:
        raise ValueError("Unexpected source activation metadata")
    sources = {r["id"]: r for r in state["scraping_sources"]}
    if set(sources) != {plan["source_id"]}:
        raise ValueError("Source cohort drift")
    source = sources[plan["source_id"]]
    applied = (source.get("metadata") or {}).get(MARKER) == plan_hash(plan)
    for key, expected_value in plan["expected_source"].items():
        if key == "updated_at" and applied:
            # The database trigger advances this bookkeeping field during activation.
            continue
        if key == "metadata" and applied:
            expected_value = dict(expected_value or {}, **plan["activation_metadata"], **{MARKER: plan_hash(plan)})
        if not same_value(key, source.get(key), expected_value):
            raise ValueError(f"Source {key} drift")
    rows = {str(row["id"]): row for row in state["shows"]}
    if len(rows) != len(expected) + plan["historical_rows_unchanged"]:
        raise ValueError("Show cohort drift")
    for ident, original in expected.items():
        row = rows.get(ident)
        if not row or row["club_id"] != plan["club_id"]:
            raise ValueError(f"Show {ident} disappeared or changed venue")
        for key, value in original.items():
            if not same_value(key, row.get(key), value):
                raise ValueError(f"Show {ident} {key} drift")
        if row.get("source_performance_id") != (updates[ident] if applied else None):
            raise ValueError(f"Show {ident} identity drift")
        urls = sorted(t["purchase_url"] for t in state["tickets"] if str(t["show_id"]) == ident)
        if urls != sorted(plan["expected_ticket_urls"][ident]) or not urls:
            raise ValueError(f"Show {ident} ticket drift")
        if {ticket_identity(url) for url in urls} != {updates[ident]}:
            raise ValueError(f"Show {ident} native identity disagrees with tickets")
    for ident, row in rows.items():
        if ident not in expected and row.get("source_performance_id") in updates.values():
            raise ValueError("Identity is already held by an unreviewed show")
    return applied


def repair(cur, plan):
    schema = lock_schema(cur)
    before = snapshot(cur, plan)
    if not validate(before, plan):
        for ident, identity in plan["identity_updates"].items():
            cur.execute(
                "UPDATE shows SET source_performance_id=%s WHERE id=%s AND club_id=%s AND source_performance_id IS NULL",
                (identity, int(ident), plan["club_id"]),
            )
            if cur.rowcount != 1:
                raise ValueError(f"Show {ident} changed during repair")
        metadata = dict(
            plan["expected_source"]["metadata"] or {}, **plan["activation_metadata"], **{MARKER: plan_hash(plan)}
        )
        cur.execute(
            "UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=%s", (json.dumps(metadata), plan["source_id"])
        )
    after = snapshot(cur, plan)
    validate(after, plan)
    if any(before[table] != after[table] for table in CHILDREN):
        raise ValueError("Repair changed existing relationships")
    return {"task_id": 4081, "plan_hash": plan_hash(plan), "schema": schema, "before": before, "after": after}


def same_business_state(left, right, source_id):
    """Compare all rows exactly except the target source's trigger-owned timestamp."""

    def normalized(state):
        result = dict(state)
        result["scraping_sources"] = sorted(
            (
                {key: value for key, value in row.items() if not (row["id"] == source_id and key == "updated_at")}
                for row in state["scraping_sources"]
            ),
            key=lambda row: json.dumps(row, sort_keys=True),
        )
        return result

    return normalized(left) == normalized(right)


def restore(cur, plan, backup):
    if backup.get("task_id") != 4081 or backup.get("plan_hash") != plan_hash(plan):
        raise ValueError("Backup does not match reviewed plan")
    if lock_schema(cur) != backup["schema"]:
        raise ValueError("Schema changed after backup")
    live = snapshot(cur, plan)
    if same_business_state(live, backup["before"], plan["source_id"]):
        return
    if live != backup["after"]:
        raise ValueError("Affected rows changed after repair; refusing restore")
    originals = {str(r["id"]): r for r in backup["before"]["shows"]}
    for ident in plan["identity_updates"]:
        cur.execute(
            "UPDATE shows SET source_performance_id=%s WHERE id=%s",
            (originals[ident].get("source_performance_id"), int(ident)),
        )
    original_source = next(r for r in backup["before"]["scraping_sources"] if r["id"] == plan["source_id"])
    cur.execute(
        "UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=%s",
        (json.dumps(original_source["metadata"]), plan["source_id"]),
    )
    if not same_business_state(snapshot(cur, plan), backup["before"], plan["source_id"]):
        raise ValueError("Restore did not reproduce original business fields and relationships")


def save_backup(path, payload):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
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

    plan = json.loads(args.plan.read_text())
    with get_transaction() as connection:
        with connection.cursor() as cur:
            if args.restore:
                restore(cur, plan, json.loads(args.restore.read_text()))
                print("RESTORED: original business fields and relationships; source updated_at refreshed by trigger")
            else:
                backup = repair(cur, plan)
                print(
                    json.dumps(
                        {
                            "mode": "apply" if args.apply else "dry_run",
                            "identity_updates": len(plan["identity_updates"]),
                            "relationships": {table: len(backup["after"][table]) for table in CHILDREN},
                        }
                    )
                )
                if args.apply:
                    save_backup(args.backup, backup)
                else:
                    connection.rollback()
                    print("DRY RUN: rolled back")


if __name__ == "__main__":
    main()
