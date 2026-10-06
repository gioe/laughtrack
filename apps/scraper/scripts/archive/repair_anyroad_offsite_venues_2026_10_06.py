#!/usr/bin/env python3
"""Repair reviewed AnyRoad offsite occurrences without replacing inventory.

Background: two shows belong at The Substation; a November class moved home.
What this script does: move two reviewed IDs, correct one future room, preserve
the historical class and all other inventory, and activate reviewed venue routes.
Usage: --build-plan plan.json --locations-file reviewed-aliases.json (read only);
       --plan plan.json [--dry-run | --apply --backup-file /private/new.json].
Restore with --rollback /private/new.json.after.json. Recovery files contain
private relationships and must never be committed. Apply snapshots before writes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from psycopg2 import sql

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.core.repair_annoyance_identity import CHILDREN, save_backup
from scripts.core.repair_seatengine_organizer_venues import (
    rows,
    digest,
    lock_schema,
    definition_ids,
    insert_definitions,
    resolve,
    assert_fields,
)

CLUB_IDS = [10970, 61212]
MOVES = {3179506, 3558318}
ROOM_ID = 3179545
HISTORICAL_ID = 3179544
FIELDS = ("club_id", "room", "production_company_id", "scraped_by_organizer_id")
MARKER = "task_4116_repair"
PRODUCER = {
    "fields": {
        "name": "The Rozzie Square Theater",
        "slug": "rozzie-square-theater",
        "website": "https://www.rozziesquaretheater.com/",
    }
}
CHANGES = [{"id": ident, "patch": {"club_id": 61212}} for ident in sorted(MOVES)] + [
    {"id": ROOM_ID, "patch": {"room": "18b Corinth Street, Boston, MA"}}
]


def build_plan(cur, locations):
    # Hash timestamp JSON in the same session timezone used by the repair lock.
    cur.execute("SET LOCAL TIME ZONE 'UTC'")
    clubs = rows(cur, "clubs", "id", CLUB_IDS)
    if {row["id"] for row in clubs} != set(CLUB_IDS):
        raise ValueError("Reviewed physical clubs missing")
    by_id = {row["id"]: row for row in clubs}
    source = rows(cur, "scraping_sources", "id", [6820])
    if (
        len(source) != 1
        or source[0]["club_id"] != 10970
        or source[0]["metadata"].get("plugin_id") != "rozziesquaretheater"
    ):
        raise ValueError("AnyRoad source identity changed")
    if MARKER in source[0]["metadata"]:
        raise ValueError("Use original plan for repeat verification, not a new post-apply plan")
    routes = []
    for location in locations:
        if location["club_id"] not in CLUB_IDS or not location["location_info"].strip():
            raise ValueError("Unreviewed location alias")
        club = by_id[location["club_id"]]
        routes.append(
            dict(
                location,
                **{key: club[key] for key in ("name", "address", "city", "state", "timezone")},
                postal_code=club["zip_code"],
            )
        )
    metadata = dict(
        source[0]["metadata"],
        anyroad_venue_routes={
            "source_id": 6820,
            "plugin_id": "rozziesquaretheater",
            "producer_id": {"$producer": "rozzie"},
            "routes": routes,
        },
    )
    return {
        "task_id": 4116,
        "clubs": {
            str(row["id"]): {
                "id": row["id"],
                "fields": {
                    key: row[key] for key in ("name", "address", "city", "state", "zip_code", "timezone", "visible")
                },
            }
            for row in clubs
        },
        "producer": PRODUCER,
        "source": {"id": 6820, "before_hash": digest(source[0]), "metadata": metadata},
        "expected_show_hashes": {str(row["id"]): digest(row) for row in rows(cur, "shows", "club_id", CLUB_IDS)},
        "changes": CHANGES,
    }


def validate_plan(plan):
    if plan.get("task_id") != 4116 or plan["changes"] != CHANGES or plan["producer"] != PRODUCER:
        raise ValueError("Only the reviewed two moves and one room correction are allowed")
    if {row["id"] for row in plan["clubs"].values()} != set(CLUB_IDS):
        raise ValueError("Physical venue identities changed")
    if not {str(ident) for ident in MOVES | {ROOM_ID, HISTORICAL_ID}} <= plan["expected_show_hashes"].keys():
        raise ValueError("Reviewed show or historical hold missing")
    source = plan["source"]
    routing = source["metadata"]["anyroad_venue_routes"]
    if (
        source["id"] != 6820
        or source["metadata"].get("plugin_id") != "rozziesquaretheater"
        or routing["source_id"] != 6820
        or routing["plugin_id"] != "rozziesquaretheater"
    ):
        raise ValueError("Source ownership/configuration changed")
    if routing["producer_id"] != {"$producer": "rozzie"} or {row["club_id"] for row in routing["routes"]} != set(
        CLUB_IDS
    ):
        raise ValueError("Routing must cover both reviewed physical venues and the real producer")


def snapshot(cur, producer_id):
    shows = rows(cur, "shows", "club_id", CLUB_IDS)
    ids = [row["id"] for row in shows]
    state = {
        "shows": shows,
        "clubs": rows(cur, "clubs", "id", CLUB_IDS),
        "sources": rows(cur, "scraping_sources", "club_id", CLUB_IDS),
        "production_companies": rows(cur, "production_companies", "id", [producer_id] if producer_id else []),
        "production_company_venues": rows(
            cur, "production_company_venues", "production_company_id", [producer_id] if producer_id else []
        ),
    }
    state.update({table: rows(cur, table, "show_id", ids) for table in CHILDREN})
    cur.execute(
        "SELECT to_jsonb(s) FROM shows s WHERE production_company_id=%s OR scraped_by_organizer_id=%s ORDER BY id",
        (producer_id, producer_id),
    )
    state["producer_shows"] = [row[0] for row in cur.fetchall()]
    cur.execute("""SELECT n.nspname,t.relname,a.attname
        FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1]
        WHERE c.contype='f' AND c.confrelid='production_companies'::regclass""")
    references = cur.fetchall()
    state["other_producer_references"] = {}
    for schema, table, column in references:
        if table in {"shows", "production_company_venues"}:
            continue
        cur.execute(sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(sql.Identifier(schema, table)))
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}=%s").format(
                sql.Identifier(schema, table), sql.Identifier(column)
            ),
            (producer_id,),
        )
        state["other_producer_references"][f"{schema}.{table}.{column}"] = sorted(
            (row[0] for row in cur.fetchall()), key=lambda row: json.dumps(row, sort_keys=True)
        )
    return state


def normalized(state):
    result = json.loads(json.dumps(state))
    for row in result["sources"]:
        row.pop("updated_at", None)
    return result


def validate_state(state, plan, producer_id):
    source = next((row for row in state["sources"] if row["id"] == 6820), None)
    if not source:
        raise ValueError("Source 6820 missing")
    marker = (source.get("metadata") or {}).get(MARKER)
    applied = bool(marker and marker.get("plan_hash") == digest(plan))
    if marker and not applied:
        raise ValueError("Another repair plan already applied")
    original = marker["source_before"] if applied else source
    if digest(original) != plan["source"]["before_hash"] or original["club_id"] != 10970:
        raise ValueError("Source before-image or ownership changed")
    if any(plan["source"]["metadata"].get(key) != value for key, value in original["metadata"].items()):
        raise ValueError("Existing source metadata must be preserved")
    if applied:
        expected = dict(
            original,
            metadata=dict(resolve(plan["source"]["metadata"], {}, {"rozzie": producer_id}), **{MARKER: marker}),
        )
        expected.pop("updated_at", None)
        assert_fields(source, expected, "source after-state")
    actual = {str(row["id"]): row for row in state["shows"]}
    if actual.keys() != plan["expected_show_hashes"].keys():
        raise ValueError("Reviewed venue inventory changed")
    for ident, row in actual.items():
        original_row = dict(row)
        if applied and ident in marker["show_fields_before"]:
            patch = next(change["patch"] for change in CHANGES if str(change["id"]) == ident)
            expected = dict(marker["show_fields_before"][ident], **patch)
            expected.update(production_company_id=producer_id, scraped_by_organizer_id=producer_id)
            assert_fields(row, expected, "repaired show")
            original_row.update(marker["show_fields_before"][ident])
        if digest(original_row) != plan["expected_show_hashes"][ident]:
            raise ValueError(f"Show {ident} before-image drift")
    return applied


def collision_guard(cur, state):
    shows = {row["id"]: row for row in state["shows"]}
    for change in CHANGES:
        row = dict(shows[change["id"]], **change["patch"])
        cur.execute(
            "SELECT id FROM shows WHERE id<>%s AND club_id=%s AND ((date=%s AND COALESCE(room,'')=%s) OR (source_performance_id IS NOT NULL AND source_performance_id=%s))",
            (row["id"], row["club_id"], row["date"], row.get("room") or "", row.get("source_performance_id")),
        )
        if cur.fetchall():
            raise ValueError("Destination occurrence/identity collision requires separate review")


def verify_preservation(before, after):
    for table in CHILDREN:
        if before[table] != after[table]:
            raise ValueError(f"Relationship changed: {table}")
    originals = {row["id"]: row for row in before["shows"]}
    for row in after["shows"]:
        original = originals[row["id"]]
        change = next((item for item in CHANGES if item["id"] == row["id"]), None)
        allowed = set(change["patch"]) | {"production_company_id", "scraped_by_organizer_id"} if change else set()
        if any(row.get(key) != value for key, value in original.items() if key not in allowed):
            raise ValueError("Unreviewed show data changed")
    for original in before["clubs"]:
        actual = next(row for row in after["clubs"] if row["id"] == original["id"])
        if any(actual.get(key) != value for key, value in original.items() if key != "total_shows"):
            raise ValueError("Physical venue identity changed")
    if [row for row in normalized(before)["sources"] if row["id"] != 6820] != [
        row for row in normalized(after)["sources"] if row["id"] != 6820
    ]:
        raise ValueError("Unrelated venue source changed")


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    definition_ids(cur, "clubs", plan["clubs"])
    producers = definition_ids(cur, "production_companies", {"rozzie": plan["producer"]})
    before = snapshot(cur, producers.get("rozzie"))
    if validate_state(before, plan, producers.get("rozzie")):
        return dict(already_applied=True, before=before, after=before, producer_id=producers["rozzie"])
    collision_guard(cur, before)
    recovery = dict(task_id=4116, plan=plan, schema=schema, before=before, created_producer=not producers)
    if backup_path:
        save_backup(backup_path, recovery)
    insert_definitions(cur, "production_companies", {"rozzie": plan["producer"]}, producers)
    producer_id = producers["rozzie"]
    old_shows = {row["id"]: row for row in before["shows"]}
    fields_before = {
        str(change["id"]): {field: old_shows[change["id"]].get(field) for field in FIELDS} for change in CHANGES
    }
    for change in CHANGES:
        row = dict(old_shows[change["id"]], **change["patch"])
        cur.execute(
            "UPDATE shows SET club_id=%s,room=%s,production_company_id=%s,scraped_by_organizer_id=%s WHERE id=%s",
            (row["club_id"], row.get("room"), producer_id, producer_id, row["id"]),
        )
        if cur.rowcount != 1:
            raise ValueError("Reviewed show disappeared")
    for club_id in CLUB_IDS:
        cur.execute(
            "INSERT INTO production_company_venues(production_company_id,club_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (producer_id, club_id),
        )
    source_before = next(row for row in before["sources"] if row["id"] == 6820)
    marker = {"plan_hash": digest(plan), "source_before": source_before, "show_fields_before": fields_before}
    metadata = dict(resolve(plan["source"]["metadata"], {}, producers), **{MARKER: marker})
    cur.execute("UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=6820", (json.dumps(metadata),))
    cur.execute(
        "UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=clubs.id) WHERE id=ANY(%s)", (CLUB_IDS,)
    )
    after = snapshot(cur, producer_id)
    validate_state(after, plan, producer_id)
    verify_preservation(before, after)
    recovery.update(already_applied=False, after=after, producer_id=producer_id)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", recovery)
    return recovery


def rollback(cur, recovery):
    if recovery.get("task_id") != 4116 or "after" not in recovery:
        raise ValueError("Full TASK-4116 recovery file required")
    lock_schema(cur)
    current = snapshot(cur, recovery["producer_id"])
    if normalized(current) == normalized(recovery["before"]):
        return False
    if normalized(current) != normalized(recovery["after"]):
        raise ValueError("Affected after-state drift; refusing rollback")
    for row in recovery["before"]["shows"]:
        if row["id"] in MOVES | {ROOM_ID}:
            cur.execute(
                "UPDATE shows SET club_id=%s,room=%s,production_company_id=%s,scraped_by_organizer_id=%s WHERE id=%s",
                (*(row[field] for field in FIELDS), row["id"]),
            )
    source = next(row for row in recovery["before"]["sources"] if row["id"] == 6820)
    cur.execute("UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=6820", (json.dumps(source["metadata"]),))
    cur.execute("DELETE FROM production_company_venues WHERE production_company_id=%s", (recovery["producer_id"],))
    for row in recovery["before"]["production_company_venues"]:
        cur.execute(
            "INSERT INTO production_company_venues(production_company_id,club_id) VALUES(%s,%s)",
            (row["production_company_id"], row["club_id"]),
        )
    if recovery["created_producer"]:
        cur.execute("DELETE FROM production_companies WHERE id=%s", (recovery["producer_id"],))
    for row in recovery["before"]["clubs"]:
        cur.execute("UPDATE clubs SET total_shows=%s WHERE id=%s", (row["total_shows"], row["id"]))
    if normalized(snapshot(cur, recovery["producer_id"])) != normalized(recovery["before"]):
        raise ValueError("Rollback failed exact preservation check")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--locations-file", type=Path)
    parser.add_argument("--backup-file", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--build-plan", type=Path)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--rollback", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup_file:
        parser.error("--apply requires --backup-file")
    if args.build_plan and not args.locations_file:
        parser.error("--build-plan requires --locations-file")
    if not args.build_plan and not args.rollback and not args.plan:
        parser.error("--plan required for repair")
    from dotenv import load_dotenv

    load_dotenv(_root / ".env")
    from laughtrack.adapters.db import get_transaction

    with get_transaction() as connection:
        with connection.cursor() as cur:
            if args.build_plan:
                plan = build_plan(cur, json.loads(args.locations_file.read_text()))
                validate_plan(plan)
                args.build_plan.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
                print("PLAN: read-only manifest created")
            elif args.rollback:
                print(json.dumps({"rollback_changed": rollback(cur, json.loads(args.rollback.read_text()))}))
            else:
                result = repair(cur, json.loads(args.plan.read_text()), args.backup_file if args.apply else None)
                print(
                    json.dumps(
                        {
                            "mode": "apply" if args.apply else "PLAN",
                            "already_applied": result["already_applied"],
                            "before_shows": len(result["before"]["shows"]),
                            "after_shows": len(result["after"]["shows"]),
                            "producer_id": result["producer_id"],
                        }
                    )
                )
        if not args.apply and not args.rollback:
            connection.rollback()
            print("PLAN: rolled back")
    if args.apply or args.rollback:
        print("COMMITTED: guarded AnyRoad repair or restoration")


if __name__ == "__main__":
    main()
