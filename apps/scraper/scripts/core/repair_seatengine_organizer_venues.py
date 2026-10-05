#!/usr/bin/env python3
"""Apply a reviewed SeatEngine organizer-to-physical-venue manifest.

Background: organizer account postal addresses are not performance venues.
What this script does: validates exact show/source before-images, creates reviewed
venues/producers, moves reviewed shows, and activates exact native routing metadata.
Usage: --plan reviewed.json [--dry-run]; --apply --backup /private/path/new.json.
Dry-run rolls back. Apply writes a private, durable recovery snapshot BEFORE writes.
Conflicting duplicate relationships abort rather than discard data. Backups contain
private user data and must never be committed. The .after.json companion records
generated IDs and the full resulting affected state for guarded manual recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Locate scraper root and support direct execution without an installed package.
_root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2 import sql

from scripts.core.repair_annoyance_identity import CHILDREN, same_value, save_backup

MARKER = "task_4109_repair"
TABLES = ("clubs", "production_companies", "production_company_venues", "scraping_sources", "shows", *CHILDREN)
CLUB_FIELDS = {"name", "address", "website", "city", "state", "zip_code", "timezone", "country", "club_type", "visible"}
PRODUCER_FIELDS = {"name", "slug", "website", "visible"}
SOURCE_FIELDS = {"enabled", "metadata", "source_url"}
CHILD_KEYS = {
    "tickets": ("type",),
    "lineup_items": ("comedian_id",),
    "tagged_shows": ("tag_id",),
    "saved_shows": ("profile_id",),
    "discovery_show_feature_snapshots": ("feature_version", "as_of"),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def validate_plan(plan):
    if plan.get("task_id") != 4109:
        raise ValueError("Expected TASK-4109 plan")
    for kind, fields in (("clubs", CLUB_FIELDS), ("producers", PRODUCER_FIELDS)):
        for symbol, definition in plan[kind].items():
            values = definition["fields"]
            if not values or set(values) - fields or not values.get("name"):
                raise ValueError(f"Invalid {kind} definition {symbol}")
            if kind == "clubs" and not definition.get("id"):
                if not all(values.get(k) for k in ("address", "website", "city", "state", "timezone")):
                    raise ValueError(f"New physical venue {symbol} lacks verified geography")
    show_ids = [row["id"] for row in plan["shows"] + plan["holds"]]
    if len(show_ids) != len(set(show_ids)):
        raise ValueError("Move/hold cohorts overlap")
    for row in plan["shows"] + plan["holds"]:
        if row in plan["holds"] and row.get("absent") is True:
            if row.get("patch"):
                raise ValueError("Absent held show cannot be patched")
            continue
        if not {"club_id", "date", "show_page_url"} <= row["before"].keys():
            raise ValueError("Each show requires exact venue/date/URL before-image")
        if row in plan["holds"] and (
            set(row.get("patch", {})) - {"is_cancelled"}
            or any(not isinstance(value, bool) for value in row.get("patch", {}).values())
        ):
            raise ValueError("Held rows permit only an explicit cancellation flag")
    for row in plan["merges"]:
        if row["from"] in show_ids or row["to"] not in show_ids or not row["before"]:
            raise ValueError("Duplicate merge must target one reviewed show")
        if set(row.get("patch", {})) - {"description"} or (row.get("patch") and not row.get("before_to")):
            raise ValueError("Merge description patch requires canonical before-image")
        for collision in row.get("coalesce", []):
            if collision.get("table") != "tickets" or not collision.get("reason"):
                raise ValueError("Explicit coalescence supports reviewed ticket aliases only")
            for key in ("before_from", "before_to"):
                if not {"id", "show_id", "price", "type", "purchase_url", "sold_out"} <= collision[key].keys():
                    raise ValueError("Ticket coalescence requires complete business before-images")
    source_ids = [row["id"] for row in plan["sources"]]
    if not source_ids or len(source_ids) != len(set(source_ids)):
        raise ValueError("Source cohort must be nonempty and unique")
    for row in plan["sources"]:
        if set(row["patch"]) - SOURCE_FIELDS or not {"club_id", "enabled", "metadata"} <= row["before"].keys():
            raise ValueError("Source patch or before-image invalid")
        if "metadata" in row["patch"] and any(
            row["patch"]["metadata"].get(key) != value for key, value in (row["before"]["metadata"] or {}).items()
        ):
            raise ValueError("Source patch must preserve existing metadata")
        if row["id"] == 294 and row["patch"].get("enabled", row["before"]["enabled"]) is not False:
            raise ValueError("Laugh Tonight source 294 must remain disabled")


def resolve(value, clubs, producers):
    if isinstance(value, dict):
        if set(value) == {"$club"}:
            return clubs[value["$club"]]
        if set(value) == {"$producer"}:
            return producers[value["$producer"]]
        return {key: resolve(item, clubs, producers) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, clubs, producers) for item in value]
    return value


def rows(cur, table, column, ids):
    cur.execute(
        sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}=ANY(%s)").format(sql.Identifier(table), sql.Identifier(column)),
        (list(ids),),
    )
    return sorted((row[0] for row in cur.fetchall()), key=lambda row: json.dumps(row, sort_keys=True))


def lock_schema(cur):
    cur.execute("SET LOCAL lock_timeout='5s'; SET LOCAL TIME ZONE 'UTC'")
    cur.execute(
        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(sql.SQL(",").join(map(sql.Identifier, TABLES)))
    )
    cur.execute("""SELECT c.conrelid::regclass::text,a.attname
        FROM pg_constraint c JOIN LATERAL unnest(c.conkey) k(attnum) ON true
        JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum
        WHERE c.confrelid='shows'::regclass AND c.contype='f'""")
    actual = {(row[0].split(".")[-1].strip('"'), row[1]) for row in cur.fetchall()}
    if actual != {(table, "show_id") for table in CHILDREN}:
        raise ValueError(f"Show foreign keys changed; recovery coverage must be reviewed: {actual}")
    # De-duplicating an identical child must not cascade an unreviewed relationship.
    cur.execute(
        "SELECT conrelid::regclass::text FROM pg_constraint WHERE contype='f' AND confrelid=ANY(%s::regclass[])",
        (list(CHILDREN),),
    )
    if cur.fetchall():
        raise ValueError("Show children have inbound references; review duplicate recovery first")
    schema = {}
    for table in TABLES:
        cur.execute(
            "SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum",
            (table,),
        )
        schema[table] = cur.fetchall()
    return schema


def definition_ids(cur, table, definitions):
    result = {}
    for symbol, definition in definitions.items():
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE name=%s").format(sql.Identifier(table)),
            (definition["fields"]["name"],),
        )
        found = cur.fetchone()
        if found:
            row = found[0]
            if definition.get("id", row["id"]) != row["id"] or any(
                not same_value(k, row.get(k), v) for k, v in definition["fields"].items()
            ):
                raise ValueError(f"{table} identity conflict: {symbol}")
            result[symbol] = row["id"]
        elif definition.get("id"):
            raise ValueError(f"Existing {table} disappeared: {symbol}")
    return result


def snapshot(cur, plan, clubs, producers):
    show_ids = {row["id"] for row in plan["shows"] + plan["holds"]} | {row["from"] for row in plan["merges"]}
    source_ids = [row["id"] for row in plan["sources"]]
    club_ids = set(clubs.values()) | {
        row["before"]["club_id"] for row in plan["shows"] + plan["holds"] + plan["sources"] if not row.get("absent")
    }
    result = {
        "clubs": rows(cur, "clubs", "id", club_ids),
        "production_companies": rows(cur, "production_companies", "id", producers.values()),
        "scraping_sources": rows(cur, "scraping_sources", "id", source_ids),
        "shows": rows(cur, "shows", "id", show_ids),
        "production_company_venues": rows(
            cur, "production_company_venues", "production_company_id", producers.values()
        ),
    }
    result.update({table: rows(cur, table, "show_id", show_ids) for table in CHILDREN})
    return result


def assert_fields(row, expected, context):
    if row is None or any(not same_value(key, row.get(key), value) for key, value in expected.items()):
        raise ValueError(f"Before/after image drift: {context}")


def validate_state(state, plan, clubs, producers):
    sources = {row["id"]: row for row in state["scraping_sources"]}
    fingerprint = digest(plan)
    markers = [(sources.get(row["id"], {}).get("metadata") or {}).get(MARKER) for row in plan["sources"]]
    applied = all(marker == fingerprint for marker in markers)
    if any(markers) and not applied:
        raise ValueError("Partial or different plan application")
    shows = {row["id"]: row for row in state["shows"]}
    for row in plan["shows"] + plan["holds"]:
        if row.get("absent") is True:
            if row["id"] in shows:
                raise ValueError(f"Absent held show {row['id']} reappeared")
            continue
        expected = dict(row["before"])
        if applied and row in plan["shows"]:
            expected.update(
                club_id=clubs[row["club"]],
                production_company_id=producers[row["producer"]],
                scraped_by_organizer_id=producers[row["producer"]],
            )
            for merge in plan["merges"]:
                if merge["to"] == row["id"]:
                    expected.update(merge.get("patch", {}))
        if applied and row in plan["holds"]:
            expected.update(row.get("patch", {}))
        assert_fields(shows.get(row["id"]), expected, f"show {row['id']}")
    for row in plan["merges"]:
        if applied:
            if row["from"] in shows:
                raise ValueError("Retired duplicate reappeared")
            tickets = {ticket["id"]: ticket for ticket in state["tickets"]}
            for collision in row.get("coalesce", []):
                if collision["from_id"] in tickets:
                    raise ValueError("Retired ticket alias reappeared")
                assert_fields(tickets.get(collision["to_id"]), collision["before_to"], "canonical ticket offer")
        else:
            assert_fields(shows.get(row["from"]), row["before"], f"duplicate {row['from']}")
            if row.get("before_to"):
                assert_fields(shows.get(row["to"]), row["before_to"], f"canonical {row['to']}")
            tickets = {ticket["id"]: ticket for ticket in state["tickets"]}
            for collision in row.get("coalesce", []):
                for key, ident, show in (("before_from", "from_id", row["from"]), ("before_to", "to_id", row["to"])):
                    assert_fields(tickets.get(collision[ident]), collision[key], f"ticket {collision[ident]}")
                    if collision[key]["id"] != collision[ident] or collision[key]["show_id"] != show:
                        raise ValueError("Ticket coalescence crosses unreviewed shows")
    for row in plan["sources"]:
        expected = dict(row["before"])
        if applied:
            expected.update(resolve(row["patch"], clubs, producers))
            expected["metadata"] = dict(expected.get("metadata") or {}, **{MARKER: fingerprint})
            expected.pop("updated_at", None)
        assert_fields(sources.get(row["id"]), expected, f"source {row['id']}")
    return applied


def insert_definitions(cur, table, definitions, identities):
    for symbol, definition in definitions.items():
        if symbol in identities:
            continue
        values = definition["fields"]
        cur.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
                sql.Identifier(table),
                sql.SQL(",").join(map(sql.Identifier, values)),
                sql.SQL(",").join(sql.Placeholder() for _ in values),
            ),
            list(values.values()),
        )
        identities[symbol] = cur.fetchone()[0]


def merge_show(cur, old, new):
    for table in CHILDREN:
        old_rows = rows(cur, table, "show_id", [old])
        new_rows = rows(cur, table, "show_id", [new])
        keys = CHILD_KEYS.get(table)
        for row in old_rows:
            collision = next(
                (
                    candidate
                    for candidate in new_rows
                    if keys and all(candidate.get(key) == row.get(key) for key in keys)
                ),
                None,
            )
            if collision:
                ignored = {"id", "show_id"}
                if any(value != collision.get(key) for key, value in row.items() if key not in ignored):
                    raise ValueError(f"Lossless merge conflict: {table} {old} -> {new}")
                condition = sql.SQL(" AND ").join(
                    sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(key)) for key in keys
                )
                cur.execute(
                    sql.SQL("DELETE FROM {} WHERE show_id=%s AND {}").format(sql.Identifier(table), condition),
                    [old, *(row[key] for key in keys)],
                )
        cur.execute(sql.SQL("UPDATE {} SET show_id=%s WHERE show_id=%s").format(sql.Identifier(table)), (new, old))
    cur.execute("DELETE FROM shows WHERE id=%s", (old,))
    if cur.rowcount != 1:
        raise ValueError("Duplicate disappeared during merge")


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    clubs = definition_ids(cur, "clubs", plan["clubs"])
    producers = definition_ids(cur, "production_companies", plan["producers"])
    before = snapshot(cur, plan, clubs, producers)
    if validate_state(before, plan, clubs, producers):
        return {"already_applied": True, "before": before, "after": before, "clubs": clubs, "producers": producers}
    recovery = {"task_id": 4109, "plan": plan, "plan_hash": digest(plan), "schema": schema, "before": before}
    if backup_path:
        save_backup(backup_path, recovery)
    insert_definitions(cur, "clubs", plan["clubs"], clubs)
    insert_definitions(cur, "production_companies", plan["producers"], producers)
    for row in plan["merges"]:
        for collision in row.get("coalesce", []):
            cur.execute("DELETE FROM tickets WHERE id=%s AND show_id=%s", (collision["from_id"], row["from"]))
            if cur.rowcount != 1:
                raise ValueError("Reviewed ticket alias disappeared")
        if row.get("patch"):
            cur.execute("UPDATE shows SET description=%s WHERE id=%s", (row["patch"]["description"], row["to"]))
        merge_show(cur, row["from"], row["to"])
    for row in plan["shows"]:
        club, producer = clubs[row["club"]], producers[row["producer"]]
        cur.execute(
            "UPDATE shows SET club_id=%s,production_company_id=%s,scraped_by_organizer_id=%s WHERE id=%s",
            (club, producer, producer, row["id"]),
        )
        if cur.rowcount != 1:
            raise ValueError("Reviewed show disappeared")
        cur.execute(
            "INSERT INTO production_company_venues(production_company_id,club_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (producer, club),
        )
    for row in plan["holds"]:
        if row.get("patch"):
            cur.execute("UPDATE shows SET is_cancelled=%s WHERE id=%s", (row["patch"]["is_cancelled"], row["id"]))
    affected_clubs = set(clubs.values()) | {row["before"]["club_id"] for row in plan["shows"] + plan["merges"]}
    cur.execute(
        "UPDATE clubs SET total_shows=(SELECT COUNT(*) FROM shows WHERE shows.club_id=clubs.id) WHERE id=ANY(%s)",
        (sorted(affected_clubs),),
    )
    originals = {row["id"]: row for row in before["scraping_sources"]}
    for row in plan["sources"]:
        patch = resolve(row["patch"], clubs, producers)
        patch["metadata"] = dict(
            patch.get("metadata", originals[row["id"]].get("metadata")) or {}, **{MARKER: digest(plan)}
        )
        cur.execute(
            sql.SQL("UPDATE scraping_sources SET {} WHERE id=%s").format(
                sql.SQL(",").join(
                    sql.SQL("{}=%s" + ("::jsonb" if key == "metadata" else "")).format(sql.Identifier(key))
                    for key in patch
                )
            ),
            [json.dumps(value) if key == "metadata" else value for key, value in patch.items()] + [row["id"]],
        )
    after = snapshot(cur, plan, clubs, producers)
    validate_state(after, plan, clubs, producers)
    recovery.update(after=after, clubs=clubs, producers=producers, already_applied=False)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", recovery)
    return recovery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private --backup path")
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
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
                    "before": {key: len(value) for key, value in result["before"].items()},
                    "after": {key: len(value) for key, value in result["after"].items()},
                    "clubs": result["clubs"],
                    "producers": result["producers"],
                }
            )
        )
        if not args.apply:
            connection.rollback()
            print("PLAN: rolled back")
    if args.apply:
        print("COMMITTED: verified routing repair")


if __name__ == "__main__":
    main()
