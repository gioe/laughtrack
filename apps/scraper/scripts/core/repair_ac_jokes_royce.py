#!/usr/bin/env python3
"""Guarded TASK-4131 Royce repair; dry-run by default, apply requires private backup.

Only three reviewed shows move. Recovery is manual: compare saved after-images
before restoring any fields; never blindly restore after subsequent scraping.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.core.repair_annoyance_identity import CHILDREN, save_backup
from scripts.core.repair_seatengine_organizer_venues import (
    definition_ids,
    digest,
    insert_definitions,
    lock_schema,
    rows,
)
from laughtrack.scrapers.implementations.api.wix_events.routing import normalized, signature

MOVE_IDS = {7898492, 7898494, 7898497}
PROTECTED_CLUBS = {412, 90822, 90823}
MARKER = "task_4131_repair"
VENUE_FIELDS = dict(
    name="The Royce Social Hall",
    address="2831 Pacific Avenue",
    city="Atlantic City",
    state="NJ",
    zip_code="08401",
    timezone="America/New_York",
    website="https://theroyceac.com/",
    visible=True,
)
LOCATION = dict(
    name="The Royce Social Hall",
    country="US",
    state="NJ",
    city="Atlantic City",
    street_number="2801",
    street_name="Pacific Avenue",
    street_apt="Suite 308",
    postal_code="08401",
)
NATIVE_SHOWS = {
    "3a929c46-de3e-443e-a4ea-a9efcb19cac2": 7898492,
    "54f73481-a918-4f0c-8a45-b42a6995f47e": 7898494,
    "2634bee1-2f29-42bf-b9a8-d23e175021ea": 7898497,
}
NATIVE_IDS = set(NATIVE_SHOWS)


def snapshot(cur, destination_id=None):
    clubs = PROTECTED_CLUBS | ({destination_id} if destination_id else set())
    shows = rows(cur, "shows", "club_id", clubs)
    ids = [r["id"] for r in shows]
    state = dict(
        shows=shows,
        clubs=rows(cur, "clubs", "id", clubs),
        production_companies=rows(cur, "production_companies", "id", [46]),
        production_company_venues=rows(cur, "production_company_venues", "production_company_id", [46]),
        scraping_sources=rows(cur, "scraping_sources", "id", [291]),
    )
    state.update({table: rows(cur, table, "show_id", ids) for table in CHILDREN})
    return state


def validate_plan(plan):
    if plan.get("task_id") != 4131 or plan.get("venue", {}).get("fields") != VENUE_FIELDS:
        raise ValueError("Expected TASK-4131 and reviewed canonical Royce venue")
    before = plan["before"]
    if set(before) != {
        "shows",
        "clubs",
        "production_companies",
        "production_company_venues",
        "scraping_sources",
        *CHILDREN,
    }:
        raise ValueError("Complete protected snapshot required")
    (source,) = before["scraping_sources"]
    if source["id"] != 291 or source["club_id"] != 412 or source["enabled"] is not True:
        raise ValueError("Unexpected source identity")
    config = source["metadata"]["wix_venue_routes"]
    if (config["source_id"], config["component_id"], config["producer_id"]) != (291, "comp-lpdlygbr", 46):
        raise ValueError("Unexpected routing identity")
    if any(signature(route["location"]) == signature(LOCATION) for route in config["routes"]):
        raise ValueError("Royce route already exists in before-image")
    (producer,) = before["production_companies"]
    if producer["id"] != 46 or producer["name"] != "AC Jokes":
        raise ValueError("Expected existing AC Jokes producer 46")
    if not PROTECTED_CLUBS <= {c["id"] for c in before["clubs"]}:
        raise ValueError("Missing protected venues")
    shows = {s["id"]: s for s in before["shows"]}
    if len(shows) != len(before["shows"]) or not MOVE_IDS <= shows.keys():
        raise ValueError("Missing or duplicate reviewed shows")
    events = plan["native_events"]
    if len(events) != 3 or {e["id"] for e in events} != NATIVE_IDS:
        raise ValueError("Unexpected native occurrence cohort")
    matched = set()
    for event in events:
        loc = event["location"]
        address = loc["fullAddress"]
        street = address["streetAddress"]
        if (
            loc.get("address")
            and address.get("formattedAddress")
            and normalized(loc["address"]) != normalized(address["formattedAddress"])
        ):
            raise ValueError("Native address fields conflict")
        if event["scheduling"]["config"].get("scheduleTbd") is not False:
            raise ValueError("Native occurrence schedule is not confirmed")
        identity = dict(
            name=loc["name"],
            country=address["country"],
            state=address["subdivision"],
            city=address["city"],
            postal_code=address["postalCode"],
            street_number=street["number"],
            street_name=street["name"],
            street_apt=street.get("apt", ""),
        )
        if loc.get("tbd") or loc.get("type", 0) != 0 or signature(identity) != signature(LOCATION):
            raise ValueError("Native venue does not match reviewed suite")
        date = datetime.fromisoformat(event["scheduling"]["config"]["startDate"].replace("Z", "+00:00"))
        matches = [
            s
            for s in shows.values()
            if s["id"] in MOVE_IDS
            and s["show_page_url"] == "https://www.acjokes.com/event-details/" + event["slug"]
            and datetime.fromisoformat(s["date"].replace("Z", "+00:00")) == date
        ]
        if (
            date.tzinfo is None
            or len(matches) != 1
            or matches[0]["id"] != NATIVE_SHOWS[event["id"]]
            or matches[0]["club_id"] != 412
            or matches[0]["room"] != LOCATION["name"]
        ):
            raise ValueError("Native occurrence does not match exact stored identity")
        matched.add(matches[0]["id"])
    if matched != MOVE_IDS:
        raise ValueError("Incomplete occurrence reconciliation")


def changed_metadata(plan, destination):
    metadata = deepcopy(plan["before"]["scraping_sources"][0]["metadata"])
    metadata["wix_venue_routes"]["routes"].append(dict(club_id=destination, location=LOCATION))
    metadata[MARKER] = digest(plan)
    return metadata


def verify_after(before, after, plan, destination):
    expected = deepcopy(before)
    for show in expected["shows"]:
        if show["id"] in MOVE_IDS:
            show.update(club_id=destination, production_company_id=46, scraped_by_organizer_id=46)
    expected["scraping_sources"][0]["metadata"] = changed_metadata(plan, destination)
    # DB-managed source timestamp is the only permitted incidental source change.
    for state in (expected, after):
        state["scraping_sources"][0].pop("updated_at", None)
    old_clubs = {c["id"]: c for c in before["clubs"]}
    for club in after["clubs"]:
        if club["id"] not in old_clubs:
            if club["id"] != destination or any(club.get(k) != v for k, v in VENUE_FIELDS.items()):
                raise ValueError("Unexpected new venue")
            expected["clubs"].append(deepcopy(club))
        else:
            original = next(c for c in expected["clubs"] if c["id"] == club["id"])
            if club["id"] in {412, destination}:
                original["total_shows"] = sum(s["club_id"] == club["id"] for s in expected["shows"])
    links = expected["production_company_venues"]
    if not any(r["club_id"] == destination for r in links):
        new = [r for r in after["production_company_venues"] if r["club_id"] == destination]
        if len(new) != 1 or new[0]["production_company_id"] != 46:
            raise ValueError("Missing producer venue link")
        links.extend(deepcopy(new))
    if any(
        sorted(expected[k], key=lambda r: json.dumps(r, sort_keys=True))
        != sorted(after[k], key=lambda r: json.dumps(r, sort_keys=True))
        for k in expected
    ):
        raise ValueError("Unexpected after-image or relationship drift")


def repair(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    definitions = {"royce": plan["venue"]}
    clubs = definition_ids(cur, "clubs", definitions)
    destination = clubs.get("royce")
    before = snapshot(cur, destination)
    marker = before["scraping_sources"][0]["metadata"].get(MARKER)
    if marker:
        if marker != digest(plan) or not destination:
            raise ValueError("Different repair plan applied")
        verify_after(plan["before"], deepcopy(before), plan, destination)
        return dict(already_applied=True, before=before, after=before, destination_id=destination)
    if before != plan["before"]:
        raise ValueError("Fresh full snapshot drift; refresh reviewed plan")
    moves = [s for s in before["shows"] if s["id"] in MOVE_IDS]
    for move in moves:
        if destination and any(s["club_id"] == destination and s["date"] == move["date"] for s in before["shows"]):
            raise ValueError("Existing destination occurrence occupies reviewed time")
    if len({s["date"] for s in moves}) != 3:
        raise ValueError("Reviewed occurrences collide")
    recovery = dict(task_id=4131, plan=plan, plan_hash=digest(plan), schema=schema, before=before)
    if backup_path:
        save_backup(backup_path, recovery)
    insert_definitions(cur, "clubs", definitions, clubs)
    destination = clubs["royce"]
    for ident in sorted(MOVE_IDS):
        cur.execute(
            "UPDATE shows SET club_id=%s,production_company_id=46,scraped_by_organizer_id=46 WHERE id=%s",
            (destination, ident),
        )
        if cur.rowcount != 1:
            raise ValueError("Reviewed show disappeared")
    cur.execute(
        "INSERT INTO production_company_venues(production_company_id,club_id) VALUES(46,%s) ON CONFLICT DO NOTHING",
        (destination,),
    )
    cur.execute(
        "UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=291",
        (json.dumps(changed_metadata(plan, destination)),),
    )
    cur.execute(
        "UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE shows.club_id=clubs.id) WHERE id=ANY(%s)",
        ([412, destination],),
    )
    after = snapshot(cur, destination)
    verify_after(before, deepcopy(after), plan, destination)
    recovery.update(already_applied=False, after=after, destination_id=destination)
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

    with get_transaction() as connection:
        with connection.cursor() as cur:
            result = repair(cur, json.loads(args.plan.read_text()), args.backup if args.apply else None)
        if not args.apply:
            connection.rollback()
        print(
            json.dumps(
                dict(
                    mode="APPLIED" if args.apply else "ROLLED BACK",
                    already_applied=result["already_applied"],
                    destination_id=result["destination_id"],
                    shows=len(result["after"]["shows"]),
                )
            )
        )


if __name__ == "__main__":
    main()
