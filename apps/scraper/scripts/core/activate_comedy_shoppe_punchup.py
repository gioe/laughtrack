#!/usr/bin/env python3
"""Activate the verified Comedy Shoppe PunchUp calendar and physical destinations.

Background: source 617 currently points to an empty ShowSlinger widget.
What this script does: provisions seven reviewed source-less physical venues and
their producer, then switches only source 617 to the verified official calendar.
Existing shows, children, organizer identity and source targets remain unchanged.
Usage: --plan reviewed.json [--dry-run]; --apply --backup /private/path/new.json.
Dry-run rolls back. Apply saves a private durable recovery snapshot before writes.
Recovery files include private data; never commit them.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Locate scraper root (apps/scraper/) by walking up to pyproject.toml, then
# put src/ + scraper root on sys.path so laughtrack and 'scripts' package imports resolve.
_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.core.repair_annoyance_identity import CHILDREN, save_backup
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

MARKER = "task_4112_activation"
SOURCE_URL = "https://www.jjcomedy.com/socials"
PAGE_ID = "4969662d-af53-4d87-b151-9f94c8f89d4c"


def validate_plan(plan):
    if plan.get("task_id") != 4112 or plan["organizer"]["id"] != 327 or plan["organizer"].get("patch"):
        raise ValueError("Expected unchanged organizer 327 and TASK-4112 plan")
    if len(plan["clubs"]) != 7 or len(plan["producers"]) != 1:
        raise ValueError("Exactly seven reviewed physical destinations and one producer required")
    for kind, allowed in (("clubs", CLUB_FIELDS), ("producers", PRODUCER_FIELDS)):
        for definition in plan[kind].values():
            fields = definition["fields"]
            if not fields.get("name") or set(fields) - allowed:
                raise ValueError("Unexpected entity definition fields")
            if kind == "clubs":
                if definition.get("id") == 327 or not all(
                    fields.get(key) for key in ("address", "city", "state", "timezone")
                ):
                    raise ValueError("Destinations must have verified physical geography")
                if fields.get("website") and not fields["website"].startswith("https://"):
                    raise ValueError("New venue website must be HTTPS or empty")
    source = plan["source"]
    patch = source["patch"]
    if source["id"] != 617 or not source.get("before_hash") or not plan["organizer"].get("before_hash"):
        raise ValueError("Source 617 must remain enabled and owned by organizer 327")
    if set(patch) != {"platform", "scraper_key", "source_url", "metadata"}:
        raise ValueError("Unexpected source mutation")
    if (patch["platform"], patch["scraper_key"], patch["source_url"]) != ("custom", "the_comedy_shoppe", SOURCE_URL):
        raise ValueError("Unexpected source replacement configuration")
    metadata = patch["metadata"]
    if MARKER in metadata:
        raise ValueError("Existing metadata must be retained; activation marker is managed internally")
    routes = metadata["punchup_venue_routes"]
    if (routes["source_id"], routes["page_id"], routes["slug"]) != (617, PAGE_ID, "comedyshoppe") or len(
        routes["routes"]
    ) != 7:
        raise ValueError("Routing source identity or venue count differs from reviewed calendar")
    checks = plan["duplicate_check"]
    if not checks["urls"] or not checks["events"]:
        raise ValueError("Duplicate checks require reviewed URLs and event identities")
    for event in checks["events"]:
        instant = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        if instant.tzinfo is None or not event["name"] or event["venue"] not in plan["clubs"]:
            raise ValueError("Duplicate event identity needs an aware timestamp and reviewed venue")


def source_patch(plan, clubs, producers, original):
    patch = resolve(plan["source"]["patch"], clubs, producers)
    routing = patch["metadata"]["punchup_venue_routes"]
    ids = [route["club_id"] for route in routing["routes"].values()]
    if set(ids) != set(clubs.values()) or len(set(ids)) != 7 or routing["producer_id"] not in producers.values():
        raise ValueError("Resolved routing destinations or producer differ from reviewed entities")
    if any(patch["metadata"].get(key) != value for key, value in (original.get("metadata") or {}).items()):
        raise ValueError("Existing source metadata must be preserved")
    patch["metadata"][MARKER] = {"plan_hash": digest(plan), "previous_source": original}
    return patch


def snapshot(cur, plan, clubs, producers):
    club_ids = set(clubs.values()) | {327} | set(plan.get("preserved_club_ids", []))
    shows = rows(cur, "shows", "club_id", club_ids)
    ids = [row["id"] for row in shows]
    cur.execute("SELECT to_jsonb(t) FROM source_targets t ORDER BY id")
    targets = [row[0] for row in cur.fetchall()]
    state = {
        "clubs": rows(cur, "clubs", "id", club_ids),
        "shows": shows,
        "scraping_sources": rows(cur, "scraping_sources", "id", [617]),
        "destination_sources": rows(cur, "scraping_sources", "club_id", clubs.values()),
        "production_companies": rows(cur, "production_companies", "id", producers.values()),
        "production_company_venues": rows(
            cur, "production_company_venues", "production_company_id", producers.values()
        ),
        "source_targets": targets,
    }
    state.update({table: rows(cur, table, "show_id", ids) for table in CHILDREN})
    return state


def validate_state(state, plan, clubs, producers):
    organizer = next((row for row in state["clubs"] if row["id"] == 327), None)
    if not organizer or digest(organizer) != plan["organizer"]["before_hash"]:
        raise ValueError("Organizer 327 before-image drift")
    if len(state["scraping_sources"]) != 1:
        raise ValueError("Source 617 missing")
    source = state["scraping_sources"][0]
    marker = (source.get("metadata") or {}).get(MARKER)
    applied = bool(marker and marker.get("plan_hash") == digest(plan))
    if marker and not applied:
        raise ValueError("Another activation plan already applied")
    original = marker["previous_source"] if applied else source
    if digest(original) != plan["source"]["before_hash"]:
        raise ValueError("Source 617 before-image drift")
    if (original["id"], original["club_id"], original["enabled"]) != (617, 327, True):
        raise ValueError("Original source ownership or enabled state changed")
    expected = dict(original)
    if applied:
        expected.update(source_patch(plan, clubs, producers, original))
        expected.pop("updated_at", None)
    assert_fields(source, expected, "source 617")
    if state["destination_sources"]:
        raise ValueError("Reviewed physical destinations must remain source-less")
    return applied


def duplicate_guard(cur, plan):
    urls = plan["duplicate_check"]["urls"]
    cur.execute(
        "SELECT id FROM shows WHERE show_page_url=ANY(%s) UNION SELECT show_id FROM tickets WHERE purchase_url=ANY(%s)",
        (urls, urls),
    )
    if cur.fetchall():
        raise ValueError("Reviewed native or ticket URL already belongs to an existing show")
    for event in plan["duplicate_check"]["events"]:
        cur.execute(
            "SELECT id FROM shows WHERE lower(trim(name))=lower(trim(%s)) AND date=%s", (event["name"], event["date"])
        )
        if cur.fetchall():
            raise ValueError("Reviewed title and instant already belong to an existing show")


def verify_preservation(before, after):
    for table in ("shows", *CHILDREN, "source_targets"):
        if before[table] != after[table]:
            raise ValueError(f"Existing data changed unexpectedly: {table}")
    current = {row["id"]: row for row in after["clubs"]}
    if any(current.get(row["id"]) != row for row in before["clubs"]):
        raise ValueError("Existing venue identity changed")


def activate(cur, plan, backup_path=None):
    validate_plan(plan)
    schema = lock_schema(cur)
    cur.execute("LOCK TABLE source_targets IN SHARE ROW EXCLUSIVE MODE")
    cur.execute(
        "SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid='source_targets'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum"
    )
    schema["source_targets"] = cur.fetchall()
    clubs = definition_ids(cur, "clubs", plan["clubs"])
    producers = definition_ids(cur, "production_companies", plan["producers"])
    before = snapshot(cur, plan, clubs, producers)
    if validate_state(before, plan, clubs, producers):
        return dict(already_applied=True, before=before, after=before, clubs=clubs, producers=producers)
    duplicate_guard(cur, plan)
    recovery = dict(task_id=4112, plan=plan, plan_hash=digest(plan), schema=schema, before=before)
    if backup_path:
        save_backup(backup_path, recovery)
    insert_definitions(cur, "clubs", plan["clubs"], clubs)
    insert_definitions(cur, "production_companies", plan["producers"], producers)
    patch = source_patch(plan, clubs, producers, before["scraping_sources"][0])
    producer = patch["metadata"]["punchup_venue_routes"]["producer_id"]
    for club in clubs.values():
        cur.execute(
            "INSERT INTO production_company_venues(production_company_id,club_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (producer, club),
        )
    cur.execute(
        "UPDATE scraping_sources SET platform=%s,scraper_key=%s,source_url=%s,metadata=%s::jsonb WHERE id=617",
        (patch["platform"], patch["scraper_key"], patch["source_url"], json.dumps(patch["metadata"])),
    )
    if cur.rowcount != 1:
        raise ValueError("Source 617 disappeared during activation")
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
            result = activate(cur, plan, args.backup if args.apply else None)
        print(
            json.dumps(
                dict(
                    mode="apply" if args.apply else "PLAN",
                    already_applied=result["already_applied"],
                    before={key: len(value) for key, value in result["before"].items()},
                    after={key: len(value) for key, value in result["after"].items()},
                    clubs=result["clubs"],
                    producers=result["producers"],
                )
            )
        )
        if not args.apply:
            connection.rollback()
            print("PLAN: rolled back")
    if args.apply:
        print("COMMITTED: verified Comedy Shoppe source activation")


if __name__ == "__main__":
    main()
