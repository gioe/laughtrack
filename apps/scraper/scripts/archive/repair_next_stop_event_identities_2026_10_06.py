#!/usr/bin/env python3
"""Reconcile reviewed Next Stop native events (TASK-4121).

Background: redirected slugs and corrected dates produced duplicate performances.
What this script does: preserve canonical IDs, move all seven child families,
backfill reviewed native identities atomically, and archive superseded public show
and ticket rows in admin_action_audits. Private recovery contains every child row;
never commit the plan or recovery files. Conflicting user data fails closed.
Usage: .venv/bin/python scripts/archive/repair_next_stop_event_identities_2026_10_06.py
  --plan /private/reviewed.json --dry-run
  --plan /private/reviewed.json --apply --backup /private/recovery.json
  --plan /private/reviewed.json --restore /private/recovery.json.after.json
Dry-run is the default and rolls back. Restore requires the exact saved after-state.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2 import sql
from scripts.core.repair_annoyance_identity import CHILDREN, same_value, save_backup
from scripts.core import repair_next_stop_alberta_wall_times as previous
from scripts.core.repair_seatengine_organizer_venues import CHILD_KEYS

TASK = 4121
ACTION = "task_4121_event_identity"
AUDIT = "admin_action_audits"
TABLES = (*previous.TABLES, AUDIT)
digest = previous.digest
timestamp = previous.timestamp


def ordered(rows):
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))


def equal_rows(actual, expected):
    # PostgreSQL normalizes timestamptz spelling; no business-field exclusions.
    return actual.keys() == expected.keys() and all(same_value(k, actual[k], v) for k, v in expected.items())


def row_index(table, rows):
    keys = ("show_id", *CHILD_KEYS[table]) if table in {"saved_shows", "tagged_shows"} else ("id",)
    result = {tuple(row[k] for k in keys): row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate primary keys in {table} before/after image")
    return result


def equal_table(table, actual, expected):
    actual, expected = row_index(table, actual), row_index(table, expected)
    return actual.keys() == expected.keys() and all(
        equal_rows(actual[key], row) for key, row in expected.items()
    )


def validate_plan(plan):
    problems = []
    if plan.get("task_id") != TASK or not plan.get("groups") or not plan.get("expected_shows"):
        raise ValueError("Expected populated TASK-4121 reviewed plan")
    if set(plan.get("expected_children", {})) != set(CHILDREN):
        problems.append("All seven child before-images are required")
    expected = {int(k): v for k, v in plan["expected_shows"].items()}
    seen, natives, removed_tickets = set(), set(), set()
    aliases = plan.get("reviewed_event_urls", {})
    for group in plan["groups"]:
        native = group["native_id"]
        try:
            valid_native = str(UUID(native)) == native
        except (ValueError, TypeError, AttributeError):
            valid_native = False
        if not valid_native or native in natives:
            problems.append("Native IDs must be distinct canonical UUIDs")
        natives.add(native)
        ids = [group["canonical_id"], *group["duplicate_ids"]]
        if len(ids) != len(set(ids)) or seen.intersection(ids) or not set(ids) <= expected.keys():
            problems.append("Groups must contain disjoint reviewed show IDs")
            continue
        seen.update(ids)
        canonical = expected[group["canonical_id"]]
        if not group.get("reason"):
            problems.append("Each group requires a reviewed reason")
        for ident in ids:
            row = expected[ident]
            if not {"id", "club_id", "date", "room", "show_page_url", "source_performance_id"} <= row.keys():
                problems.append("Incomplete show identity before-image")
                continue
            if row["club_id"] != canonical["club_id"] or row.get("room") != canonical.get("room"):
                problems.append("Merge crosses venue or room")
            if row["club_id"] not in plan["cohort_club_ids"]:
                problems.append("Venue is outside the reviewed cohort")
            if row["source_performance_id"] not in (None, f"next_stop_comedy:{native}"):
                problems.append("Show already belongs to a different native identity")
            if aliases.get(row["show_page_url"]) != native:
                problems.append("Original show URL lacks reviewed native identity evidence")
            historical = timestamp(row["date"]) <= timestamp(plan["captured_at"])
            if historical and group.get("allow_historical") is not True:
                problems.append("Historical source requires explicit review")
        target_url = group["target_url"]
        if aliases.get(target_url) != native:
            problems.append("Target URL lacks reviewed native identity evidence")
        parsed = urlsplit(target_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "www.nextstopcomedy.com"
            or not parsed.path.startswith("/events/")
        ):
            problems.append("Unexpected target source URL")
        if (
            timestamp(group["target_date"]) <= timestamp(plan["captured_at"])
            and group.get("allow_historical") is not True
        ):
            problems.append("Historical target requires explicit review")
        for collision in group.get("ticket_coalescences", []):
            old, keep = collision["before_from"], collision["before_to"]
            if (
                old.get("id") != collision["from_id"]
                or keep.get("id") != collision["to_id"]
                or old["id"] == keep["id"]
                or old["id"] in removed_tickets
                or old.get("show_id") not in ids
                or keep.get("show_id") not in ids
                or old.get("type") != keep.get("type")
                or not collision.get("reason")
            ):
                problems.append("Invalid explicit ticket conflict disposition")
            removed_tickets.add(old["id"])
        for update in group.get("proposed_ticket_updates", []):
            if (
                update["before"].get("id") != update["id"]
                or update["before"].get("show_id") != group["canonical_id"]
                or not update.get("reason")
                or not update.get("patch")
                or not set(update["patch"]) <= {"price", "purchase_url"}
                or update["id"] in removed_tickets
            ):
                problems.append("Invalid reviewed ticket update")
            if "purchase_url" in update["patch"] and aliases.get(update["patch"]["purchase_url"]) != native:
                problems.append("Ticket target URL lacks native identity evidence")
        if set(group.get("proposed_show_patch", {})) - {"min_price"}:
            problems.append("Only trigger-derived price may appear in proposed show patch")
    if problems:
        raise ValueError("; ".join(problems))


def lock_schema(cur):
    cur.execute("SET LOCAL lock_timeout='5s'; SET LOCAL TIME ZONE 'UTC'")
    cur.execute(
        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(
            sql.SQL(",").join(map(sql.Identifier, TABLES))
        )
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
    # Fetch complete schema fingerprints for all tables in one network trip.
    cur.execute(
        """SELECT t.name,jsonb_build_object(
        'columns', (SELECT jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod)) ORDER BY a.attnum)
            FROM pg_attribute a WHERE a.attrelid=t.name::regclass AND a.attnum>0 AND NOT a.attisdropped),
        'primary', (SELECT jsonb_agg(a.attname ORDER BY k.ord)
            FROM pg_index i JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,ord) ON true
            JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum
            WHERE i.indrelid=t.name::regclass AND i.indisprimary),
        'constraints', COALESCE((SELECT jsonb_agg(jsonb_build_array(c.conname,pg_get_constraintdef(c.oid)) ORDER BY c.conname)
            FROM pg_constraint c WHERE c.conrelid=t.name::regclass),'[]'::jsonb),
        'indexes', COALESCE((SELECT jsonb_agg(jsonb_build_array(pg_get_indexdef(i.indexrelid)) ORDER BY i.indexrelid::regclass::text)
            FROM pg_index i WHERE i.indrelid=t.name::regclass),'[]'::jsonb),
        'triggers', COALESCE((SELECT jsonb_agg(jsonb_build_array(pg_get_triggerdef(g.oid)) ORDER BY g.tgname)
            FROM pg_trigger g WHERE g.tgrelid=t.name::regclass AND NOT g.tgisinternal),'[]'::jsonb)
        ) FROM unnest(%s::text[]) AS t(name)""",
        (list(TABLES),),
    )
    schema = dict(cur.fetchall())
    if any(not schema[t]["primary"] for t in TABLES):
        raise ValueError("Every affected table requires a reviewed primary key")
    required_audit = {
        "id",
        "actor_profile_id",
        "action",
        "entity_type",
        "entity_id",
        "reason",
        "before_json",
        "after_json",
        "created_at",
    }
    if not required_audit <= dict(schema[AUDIT]["columns"]).keys():
        raise ValueError("Audit archive schema changed")
    if "source_performance_id" not in dict(schema["shows"]["columns"]):
        raise ValueError("Source identity schema is missing")
    return schema


def snapshot(cur, plan):
    ids = list(map(int, plan["expected_shows"]))
    cur.execute(
        "SELECT id FROM shows WHERE (club_id=ANY(%s) AND date>=%s) OR id=ANY(%s) OR source_performance_id=ANY(%s)",
        (
            plan["cohort_club_ids"],
            plan.get("snapshot_floor", plan["captured_at"]),
            ids,
            [f"next_stop_comedy:{g['native_id']}" for g in plan["groups"]],
        ),
    )
    ids = set(ids) | {row[0] for row in cur.fetchall()}
    # One round trip for every target, including corrected historical slots.
    targets = [
        (
            plan["expected_shows"][str(g["canonical_id"])]["club_id"],
            g["target_date"],
            plan["expected_shows"][str(g["canonical_id"])].get("room"),
        )
        for g in plan["groups"]
    ]
    cur.execute(
        """SELECT s.id FROM shows s JOIN
        unnest(%s::int[],%s::timestamptz[],%s::text[]) AS target(club_id,date,room)
        ON s.club_id=target.club_id AND s.date=target.date AND s.room IS NOT DISTINCT FROM target.room""",
        tuple(list(values) for values in zip(*targets)),
    )
    ids.update(row[0] for row in cur.fetchall())
    state = {}
    for table in previous.TABLES:
        column, values = (
            ("id", plan["cohort_club_ids"])
            if table == "clubs"
            else (
                ("id", [plan["organizer_id"]])
                if table == "production_companies"
                else ("id", sorted(ids)) if table == "shows" else ("show_id", sorted(ids))
            )
        )
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}=ANY(%s)").format(
                sql.Identifier(table), sql.Identifier(column)
            ),
            (values,),
        )
        state[table] = ordered(row[0] for row in cur.fetchall())
    cur.execute(
        sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE action=%s").format(sql.Identifier(AUDIT)), (ACTION,)
    )
    state[AUDIT] = ordered(row[0] for row in cur.fetchall())
    return state


def planned_state(before, plan):
    """Pure lossless simulation, also used to reject conflicts before any writes."""
    after = copy.deepcopy(before)
    shows = {r["id"]: r for r in after["shows"]}
    archives = []
    for group in plan["groups"]:
        canonical = group["canonical_id"]
        for ident in [canonical, *group["duplicate_ids"]]:
            archives.append(("show", ident, copy.deepcopy(shows[ident]), canonical, None, group["reason"]))
        for collision in group.get("ticket_coalescences", []):
            tickets = {r["id"]: r for r in after["tickets"]}
            for key, ident in (("before_from", collision["from_id"]), ("before_to", collision["to_id"])):
                if ident not in tickets or not equal_rows(tickets[ident], collision[key]):
                    raise ValueError("Explicit ticket disposition before-image drift")
            removed = tickets[collision["from_id"]]
            archives.append(
                (
                    "ticket",
                    removed["id"],
                    copy.deepcopy(removed),
                    canonical,
                    collision["to_id"],
                    collision["reason"],
                )
            )
            after["tickets"].remove(removed)
        for update in group.get("proposed_ticket_updates", []):
            ticket = next((r for r in after["tickets"] if r["id"] == update["id"]), None)
            if ticket is None or not equal_rows(ticket, update["before"]):
                raise ValueError("Reviewed ticket update before-image drift")
            archives.append(
                ("ticket", ticket["id"], copy.deepcopy(ticket), canonical, ticket["id"], update["reason"])
            )
            ticket.update(update["patch"])
        for old in group["duplicate_ids"]:
            for table in CHILDREN:
                keys = CHILD_KEYS.get(table)
                existing = [r for r in after[table] if r["show_id"] == canonical]
                for row in list(after[table]):
                    if row["show_id"] != old:
                        continue
                    collision = next(
                        (r for r in existing if keys and all(r.get(k) == row.get(k) for k in keys)), None
                    )
                    if collision:
                        if any(v != collision.get(k) for k, v in row.items() if k not in {"id", "show_id"}):
                            raise ValueError(f"Unreviewed lossless merge conflict in {table}")
                        after[table].remove(row)
                    else:
                        row["show_id"] = canonical
                        existing.append(row)
            del shows[old]
        shows[canonical].update(
            date=group["target_date"],
            show_page_url=group["target_url"],
            source_performance_id=f"next_stop_comedy:{group['native_id']}",
        )
        # Predict the existing ticket triggers; never write these derived fields.
        tickets = [r for r in after["tickets"] if r["show_id"] == canonical]
        if "min_price" in shows[canonical]:
            shows[canonical]["min_price"] = min(
                (r["price"] for r in tickets if r["price"] is not None and r["price"] > 0), default=None
            )
        if "tickets_sold_out" in shows[canonical]:
            shows[canonical]["tickets_sold_out"] = bool(tickets) and all(r["sold_out"] for r in tickets)
    after["shows"] = list(shows.values())
    return {table: ordered(rows) for table, rows in after.items()}, archives


def validate_before(state, plan):
    problems = []
    expectations = {
        "clubs": list(plan["expected_clubs"].values()),
        "production_companies": [plan["expected_organizer"]],
        "shows": list(plan["expected_shows"].values()),
        **plan["expected_children"],
        AUDIT: [],
    }
    for table, expected in expectations.items():
        # Full JSON rows, including private child before-images, are required.
        if not equal_table(table, state[table], expected):
            problems.append(f"Exact {table} before-image drift")
    retired = {ident for g in plan["groups"] for ident in g["duplicate_ids"]}
    targets = set()
    for group in plan["groups"]:
        row = plan["expected_shows"][str(group["canonical_id"])]
        key = (row["club_id"], timestamp(group["target_date"]), row.get("room"))
        if key in targets:
            problems.append("Reviewed destination collision")
        targets.add(key)
        for other in state["shows"]:
            if (
                other["id"] not in retired | {group["canonical_id"]}
                and (other["club_id"], timestamp(other["date"]), other.get("room")) == key
            ):
                problems.append("Unreviewed physical-slot collision")
    if problems:
        raise ValueError("; ".join(problems))


def assert_state(actual, expected):
    for table in TABLES:
        if not equal_table(table, actual[table], expected[table]):
            raise ValueError(f"Unexpected {table} change; preservation failed")


def matching_keys(keys):
    # PostgreSQL primary keys are non-null. Equality permits index/hash joins;
    # IS NOT DISTINCT FROM would scan large click tables per incoming row.
    return sql.SQL(" AND ").join(
        sql.SQL("t.{} = r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys
    )


def delete_rows(cur, table, rows, keys):
    if not rows:
        return
    cur.execute(
        sql.SQL("DELETE FROM {} t USING jsonb_populate_recordset(NULL::{},%s::jsonb) r WHERE {}").format(
            sql.Identifier(table), sql.Identifier(table), matching_keys(keys)
        ),
        (json.dumps(rows),),
    )
    if cur.rowcount != len(rows):
        raise ValueError(f"{table} bulk delete count drift")


def update_rows(cur, table, rows, keys, fields=None):
    if not rows:
        return
    columns = fields if fields is not None else [k for k in rows[0] if k not in keys]
    sets = sql.SQL(",").join(sql.SQL("{}=r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in columns)
    cur.execute(
        sql.SQL("UPDATE {} t SET {} FROM jsonb_populate_recordset(NULL::{},%s::jsonb) r WHERE {}").format(
            sql.Identifier(table), sets, sql.Identifier(table), matching_keys(keys)
        ),
        (json.dumps(rows),),
    )
    if cur.rowcount != len(rows):
        raise ValueError(f"{table} bulk update count drift")


def insert_rows(cur, table, rows, fields=None):
    if not rows:
        return
    columns = list(fields if fields is not None else rows[0])
    names = sql.SQL(",").join(map(sql.Identifier, columns))
    cur.execute(
        sql.SQL("INSERT INTO {} ({}) SELECT {} FROM jsonb_populate_recordset(NULL::{},%s::jsonb)").format(
            sql.Identifier(table), names, names, sql.Identifier(table)
        ),
        (json.dumps(rows),),
    )
    if cur.rowcount != len(rows):
        raise ValueError(f"{table} bulk insert count drift")


def apply_table_delta(cur, table, before, after, keys):
    old = {tuple(r[k] for k in keys): r for r in before}
    new = {tuple(r[k] for k in keys): r for r in after}
    delete_rows(cur, table, [r for key, r in old.items() if key not in new], keys)
    update_rows(cur, table, [r for key, r in new.items() if key in old and not equal_rows(r, old[key])], keys)
    insert_rows(cur, table, [r for key, r in new.items() if key not in old])


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    before = snapshot(cur, plan)
    # Reconstruct reviewed state, including unchanged inventory, to validate a
    # repeat invocation; the durable per-row archives bind it to this exact plan.
    original = {
        "clubs": list(plan["expected_clubs"].values()),
        "production_companies": [plan["expected_organizer"]],
        "shows": list(plan["expected_shows"].values()),
        **plan["expected_children"],
        AUDIT: [],
    }
    expected, archives = planned_state(original, plan)
    if before[AUDIT]:
        validate_archives(before[AUDIT], archives, plan)
        expected[AUDIT] = before[AUDIT]
        assert_state(before, expected)
        return dict(already_applied=True, before=before, after=before)
    validate_before(before, plan)
    expected, archives = planned_state(before, plan)
    recovery = dict(
        task_id=TASK,
        plan=plan,
        plan_hash=digest(plan),
        schema=schema,
        before=before,
        before_hash=digest(before),
    )
    if backup_path:
        save_backup(backup_path, recovery)
    archive_rows = []
    for kind, ident, row, canonical, kept, reason in archives:
        payload = dict(task_id=TASK, plan_hash=digest(plan), canonical_show_id=canonical, kept_ticket_id=kept)
        archive_rows.append(
            dict(
                actor_profile_id=None,
                action=ACTION,
                entity_type=kind,
                entity_id=str(ident),
                reason=reason,
                before_json=row,
                after_json=payload,
            )
        )
    insert_rows(cur, AUDIT, archive_rows)
    canonical_ids = {g["canonical_id"] for g in plan["groups"]}
    update_rows(
        cur,
        "shows",
        [r for r in expected["shows"] if r["id"] in canonical_ids],
        ["id"],
        fields=["date", "show_page_url", "source_performance_id"],
    )
    # planned_state already proved every merge/coalescence lossless. Execute the
    # exact image delta per table, not thousands of network round trips per row.
    for table in CHILDREN:
        apply_table_delta(cur, table, before[table], expected[table], schema[table]["primary"])
    retained = {r["id"] for r in expected["shows"]}
    delete_rows(cur, "shows", [r for r in before["shows"] if r["id"] not in retained], ["id"])
    after = snapshot(cur, plan)
    validate_archives(after[AUDIT], archives, plan)
    expected[AUDIT] = after[AUDIT]
    assert_state(after, expected)
    recovery.update(after=after, after_hash=digest(after), already_applied=False)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", recovery)
    return recovery


def validate_archives(actual, archives, plan):
    if len(actual) != len(archives):
        raise ValueError("Durable archive count drift")
    for kind, ident, row, canonical, kept, reason in archives:
        matches = [a for a in actual if a["entity_type"] == kind and a["entity_id"] == str(ident)]
        payload = dict(task_id=TASK, plan_hash=digest(plan), canonical_show_id=canonical, kept_ticket_id=kept)
        if (
            len(matches) != 1
            or matches[0]["before_json"] != row
            or matches[0]["after_json"] != payload
            or matches[0]["reason"] != reason
            or matches[0]["actor_profile_id"] is not None
        ):
            raise ValueError("Durable archive content drift")


def restore(cur, plan, backup):
    if backup.get("task_id") != TASK or backup.get("plan_hash") != digest(plan):
        raise ValueError("Recovery does not match the reviewed plan")
    if lock_schema(cur) != backup["schema"]:
        raise ValueError("Schema changed since recovery snapshot")
    if any(digest(backup[p]) != backup[p + "_hash"] for p in ("before", "after")):
        raise ValueError("Recovery checksum mismatch")
    live = snapshot(cur, plan)
    if live == backup["before"]:
        return
    if live != backup["after"]:
        raise ValueError("Affected state changed after repair; refusing restore")
    # First restore canonical show dates/identities, freeing slots occupied by
    # merged duplicates, then insert missing shows and restore every child row.
    for table in TABLES:
        apply_table_delta(
            cur, table, backup["after"][table], backup["before"][table], backup["schema"][table]["primary"]
        )
    if snapshot(cur, plan) != backup["before"]:
        raise ValueError("Recovery did not reproduce the exact original state")


def main():
    parser = argparse.ArgumentParser(description="Guarded reviewed Next Stop event identity repair")
    parser.add_argument("--plan", required=True, type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--apply", action="store_true")
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
            else:
                result = repair(cur, plan, args.backup if args.apply else None)
                for phase in ("before", "after"):
                    print(
                        ("APPLY " if args.apply else "PLAN ")
                        + phase.upper()
                        + " "
                        + json.dumps({t: len(rows) for t, rows in result[phase].items()})
                    )
                print(json.dumps({"already_applied": result["already_applied"]}))
        if not args.apply and not args.restore:
            connection.rollback()
            print("PLAN: rolled back")
    if args.apply or args.restore:
        print("Transaction committed")


if __name__ == "__main__":
    main()
