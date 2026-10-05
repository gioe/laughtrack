#!/usr/bin/env python3
"""Move three reviewed AC Jokes performances to their physical venues.

Background: organizer account 412 mixes Resorts, Hi Point and Cove performances.
What this script does: validates the reviewed cohort, moves only three existing
shows, preserves every relationship and the Resorts cohort, and configures source
291 with reviewed physical venue routes. It never deletes or merges shows.
Usage: --plan reviewed.json [--dry-run]; --apply --backup /private/path/new.json.
Dry-run rolls back. Apply requires a private recovery snapshot before any writes.
Backups include private relationship data; never commit them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Locate scraper root (apps/scraper/) by walking up to pyproject.toml, then
# put src/ + scraper root on sys.path so laughtrack and 'scripts' package imports resolve.
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.core.repair_annoyance_identity import CHILDREN, same_value, save_backup
from scripts.core.repair_seatengine_organizer_venues import (
    CLUB_FIELDS,
    PRODUCER_FIELDS,
    assert_fields,
    definition_ids,
    digest,
    insert_definitions,
    lock_schema,
    resolve,
    rows,
)

MOVE_IDS = {6537828, 6537839, 7475796}
ABSENT_ID = 6537818
MARKER = "task_4110_repair"


def validate_plan(plan):
    if plan.get("task_id") != 4110 or plan.get("merges"):
        raise ValueError("Expected TASK-4110 plan without merges")
    if {row["id"] for row in plan["shows"]} != MOVE_IDS or len(plan["shows"]) != 3:
        raise ValueError("Only the three reviewed existing shows may move")
    present_holds = [row for row in plan["holds"] if not row.get("absent")]
    absent = [row["id"] for row in plan["holds"] if row.get("absent")]
    if len(present_holds) < 40 or ABSENT_ID not in absent:
        raise ValueError("Expected at least forty preserved Resorts shows and reviewed absent show")
    ids = [row["id"] for row in plan["shows"] + plan["holds"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Reviewed cohorts overlap")
    for row in plan["shows"] + present_holds:
        if not {"id", "club_id", "date", "show_page_url"} <= row["before"].keys() or row.get("patch"):
            raise ValueError("Every present show requires exact identity; no extra patches")
        if row["before"]["id"] != row["id"] or row["before"]["club_id"] != 412:
            raise ValueError("Reviewed original shows must belong to Resorts account 412")
    for kind, allowed in (("clubs", CLUB_FIELDS), ("producers", PRODUCER_FIELDS)):
        for symbol, definition in plan[kind].items():
            fields = definition["fields"]
            if not fields.get("name") or set(fields) - allowed:
                raise ValueError(f"Invalid {kind} definition {symbol}")
            if kind == "clubs" and not definition.get("id"):
                if not all(fields.get(key) for key in ("address", "city", "state", "timezone", "website")):
                    raise ValueError("New venue requires verified geography")
                if not fields["website"].startswith("https://"):
                    raise ValueError("New venue website must use HTTPS")
    if len(plan["sources"]) != 1 or plan["sources"][0]["id"] != 291:
        raise ValueError("Only source 291 may change")
    source = plan["sources"][0]
    if source["before"].get("club_id") != 412 or set(source["patch"]) != {"metadata"}:
        raise ValueError("Source ownership and enabled state must remain unchanged")
    metadata = source["patch"]["metadata"]
    if any(metadata.get(key) != value for key, value in (source["before"].get("metadata") or {}).items()):
        raise ValueError("Existing source metadata must be preserved")
    route = metadata.get("wix_venue_routes", {})
    if route.get("source_id") != 291 or route.get("component_id") != "comp-lpdlygbr":
        raise ValueError("Source routing identity changed")


def snapshot(cur, plan, clubs, producers):
    ids = [row["id"] for row in plan["shows"] + plan["holds"]]
    state = {
        "shows": rows(cur, "shows", "id", ids),
        "clubs": rows(cur, "clubs", "id", set(clubs.values()) | {412}),
        "production_companies": rows(cur, "production_companies", "id", producers.values()),
        "production_company_venues": rows(
            cur, "production_company_venues", "production_company_id", producers.values()
        ),
        "scraping_sources": rows(cur, "scraping_sources", "id", [291]),
    }
    state.update({table: rows(cur, table, "show_id", ids) for table in CHILDREN})
    return state


def validate_state(state, plan, clubs, producers):
    if len(state["scraping_sources"]) != 1:
        raise ValueError("Source 291 missing")
    source = state["scraping_sources"][0]
    marker = (source.get("metadata") or {}).get(MARKER)
    applied = marker == digest(plan)
    if marker and not applied:
        raise ValueError("Different repair plan already applied")
    expected = dict(plan["sources"][0]["before"])
    if applied:
        expected["metadata"] = dict(
            resolve(plan["sources"][0]["patch"]["metadata"], clubs, producers), **{MARKER: digest(plan)}
        )
        expected.pop("updated_at", None)
    assert_fields(source, expected, "source 291")
    actual = {row["id"]: row for row in state["shows"]}
    if set(actual) != MOVE_IDS | {row["id"] for row in plan["holds"] if not row.get("absent")}:
        raise ValueError("Reviewed show cohort disappeared or absent show reappeared")
    for row in plan["shows"] + plan["holds"]:
        if row.get("absent"):
            continue
        expected = dict(row["before"])
        if applied and row["id"] in MOVE_IDS:
            expected.update(
                club_id=clubs[row["club"]],
                production_company_id=producers[row["producer"]],
                scraped_by_organizer_id=producers[row["producer"]],
            )
        assert_fields(actual[row["id"]], expected, f"show {row['id']}")
    return applied


def assert_no_collisions(cur, plan, clubs):
    targets = set()
    for row in plan["shows"]:
        destination = clubs.get(row["club"])
        original = row["before"]
        key = (row["club"], original["date"], original.get("room") or "")
        if key in targets:
            raise ValueError("Reviewed moves collide at one physical slot")
        targets.add(key)
        if destination:
            cur.execute(
                "SELECT id FROM shows WHERE club_id=%s AND date=%s AND COALESCE(room,'')=%s AND id<>%s",
                (destination, original["date"], original.get("room") or "", row["id"]),
            )
            if cur.fetchall():
                raise ValueError("Existing destination show occupies reviewed physical slot")


def verify_preservation(before, after):
    originals = {row["id"]: row for row in before["shows"]}
    results = {row["id"]: row for row in after["shows"]}
    if originals.keys() != results.keys():
        raise ValueError("Show identities changed unexpectedly")
    for ident, original in originals.items():
        allowed = {"club_id", "production_company_id", "scraped_by_organizer_id"} if ident in MOVE_IDS else set()
        if any(
            not same_value(key, results[ident].get(key), value) for key, value in original.items() if key not in allowed
        ):
            raise ValueError(f"Unreviewed show fields changed: {ident}")
    for table in CHILDREN:
        if before[table] != after[table]:
            raise ValueError(f"Relationship changed unexpectedly: {table}")
    original = next(row for row in before["clubs"] if row["id"] == 412)
    result = next(row for row in after["clubs"] if row["id"] == 412)
    if any(not same_value(key, result.get(key), value) for key, value in original.items() if key != "total_shows"):
        raise ValueError("Original Resorts club identity changed")


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    clubs = definition_ids(cur, "clubs", plan["clubs"])
    producers = definition_ids(cur, "production_companies", plan["producers"])
    before = snapshot(cur, plan, clubs, producers)
    applied = validate_state(before, plan, clubs, producers)
    expected_resorts = {row["id"] for row in plan["holds"] if not row.get("absent")}
    if not applied:
        expected_resorts |= MOVE_IDS
    cur.execute("SELECT id FROM shows WHERE club_id=412")
    if {row[0] for row in cur.fetchall()} != expected_resorts:
        raise ValueError("Source club inventory differs from reviewed cohort")
    if applied:
        return dict(already_applied=True, before=before, after=before, clubs=clubs, producers=producers)
    assert_no_collisions(cur, plan, clubs)
    recovery = dict(task_id=4110, plan=plan, plan_hash=digest(plan), schema=schema, before=before)
    if backup_path:
        save_backup(backup_path, recovery)
    insert_definitions(cur, "clubs", plan["clubs"], clubs)
    insert_definitions(cur, "production_companies", plan["producers"], producers)
    for row in plan["shows"]:
        club, producer = clubs[row["club"]], producers[row["producer"]]
        cur.execute(
            "UPDATE shows SET club_id=%s,production_company_id=%s,scraped_by_organizer_id=%s WHERE id=%s",
            (club, producer, producer, row["id"]),
        )
        if cur.rowcount != 1:
            raise ValueError("Reviewed show disappeared")
        cur.execute(
            "INSERT INTO production_company_venues(production_company_id,club_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (producer, club),
        )
    metadata = dict(resolve(plan["sources"][0]["patch"]["metadata"], clubs, producers), **{MARKER: digest(plan)})
    routing = metadata["wix_venue_routes"]
    if routing["producer_id"] not in producers.values():
        raise ValueError("Routing producer must be a reviewed production company")
    for route in routing["routes"]:
        if route["club_id"] not in clubs.values():
            raise ValueError("Routing destination must be a reviewed physical venue")
        cur.execute(
            "INSERT INTO production_company_venues(production_company_id,club_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (routing["producer_id"], route["club_id"]),
        )
    cur.execute("UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=291", (json.dumps(metadata),))
    cur.execute(
        "UPDATE clubs SET total_shows=(SELECT COUNT(*) FROM shows WHERE shows.club_id=clubs.id) WHERE id=ANY(%s)",
        (list(set(clubs.values()) | {412}),),
    )
    after = snapshot(cur, plan, clubs, producers)
    validate_state(after, plan, clubs, producers)
    verify_preservation(before, after)
    recovery.update(already_applied=False, after=after, clubs=clubs, producers=producers)
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

    load_dotenv(_root / ".env")
    from laughtrack.adapters.db import get_transaction

    plan = json.loads(args.plan.read_text())
    with get_transaction() as connection:
        with connection.cursor() as cur:
            result = repair(cur, plan, args.backup if args.apply else None)
        print(
            json.dumps(
                dict(
                    mode="apply" if args.apply else "PLAN",
                    already_applied=result["already_applied"],
                    before={k: len(v) for k, v in result["before"].items()},
                    after={k: len(v) for k, v in result["after"].items()},
                    clubs=result["clubs"],
                    producers=result["producers"],
                )
            )
        )
        if not args.apply:
            connection.rollback()
            print("PLAN: rolled back")
    if args.apply:
        print("COMMITTED: verified AC Jokes venue repair")


if __name__ == "__main__":
    main()
