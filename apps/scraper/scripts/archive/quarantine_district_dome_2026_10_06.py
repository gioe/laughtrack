#!/usr/bin/env python3
"""Quarantine verified District Dome non-comedy inventory without deleting it.

Background: District Dome has a mismatched Carry On description and reservation.
What this script does: hide/classify the venue, correct prose, disable source 87.
Usage: --capture private.json; --before-file private.json --dry-run;
       --before-file private.json --apply --backup-file private-recovery.json.
Rollback: --rollback private-recovery.json. Private snapshots contain references;
never commit them. Every direct club/show FK is locked and preserved.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

from psycopg2 import sql

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from scripts.core.repair_annoyance_identity import save_backup
from scripts.core.repair_seatengine_organizer_venues import digest, rows

MARKER = "task_4117_disposition"
DESCRIPTION = (
    "Seasonal immersive dining and cocktail experience at Desert Ridge Marketplace "
    "in Phoenix, Arizona; not a comedy venue. District Dome is distinct from the "
    "Carry On cocktail experience downtown."
)
FIELDS = ("visible", "club_type", "description")


def relationships(cur, lock=True):
    cur.execute("SET LOCAL TIME ZONE 'UTC'; SET LOCAL lock_timeout='5s'")
    if lock:
        cur.execute("LOCK TABLE clubs,shows,scraping_sources IN SHARE ROW EXCLUSIVE MODE")
    cur.execute("""SELECT n.nspname,t.relname,a.attname,p.relname,b.attname,array_length(c.conkey,1)
        FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
        JOIN pg_class p ON p.oid=c.confrelid JOIN pg_namespace n ON n.oid=t.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1]
        JOIN pg_attribute b ON b.attrelid=c.confrelid AND b.attnum=c.confkey[1]
        WHERE c.contype='f' AND c.confrelid IN ('clubs'::regclass,'shows'::regclass)
        ORDER BY n.nspname,t.relname,a.attname,p.relname""")
    refs = cur.fetchall()
    if any(target != "id" or width != 1 for _, _, _, _, target, width in refs):
        raise ValueError("Unexpected foreign-key shape; review snapshot coverage")
    if lock:
        for schema, table in sorted({(r[0], r[1]) for r in refs}):
            cur.execute(sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(sql.Identifier(schema, table)))
    return refs


def snapshot(cur, refs):
    state = {
        "club": rows(cur, "clubs", "id", [554]),
        "sources": rows(cur, "scraping_sources", "club_id", [554]),
        "shows": rows(cur, "shows", "club_id", [554]),
        "references": {},
    }
    show_ids = [r["id"] for r in state["shows"]]
    for schema, table, column, parent, _, _ in refs:
        if table in {"shows", "scraping_sources"}:
            continue
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}=ANY(%s)").format(
                sql.Identifier(schema, table), sql.Identifier(column)
            ),
            ([554] if parent == "clubs" else show_ids,),
        )
        state["references"][f"{schema}.{table}.{column}"] = sorted(
            (r[0] for r in cur.fetchall()), key=lambda r: json.dumps(r, sort_keys=True)
        )
    return state


def normalized(state):
    result = deepcopy(state)
    for source in result["sources"]:
        source.pop("updated_at", None)
    return result


def validate_before(before):
    problems = []
    if len(before.get("club", [])) != 1 or len(before.get("sources", [])) != 1:
        raise ValueError("Expected exactly one reviewed club and source")
    club, source = before["club"][0], before["sources"][0]
    pins = {
        "id": 554,
        "name": "District Dome",
        "address": "21001 N Tatum Blvd, Phoenix, AZ 85050, USA",
        "zip_code": "85050",
        "city": "Phoenix",
        "state": "AZ",
        "timezone": "America/Phoenix",
        "google_place_id": "ChIJ_y7Ne-BwK4cR7wtdsKrbYgw",
        "visible": True,
        "status": "active",
    }
    if any(club.get(k) != v for k, v in pins.items()):
        problems.append("District Dome physical identity or disposition changed")
    if "WREN & WOLF" not in (club.get("description") or "").upper():
        problems.append("Reviewed contaminated description changed")
    pins = {
        "id": 87,
        "club_id": 554,
        "seatengine_id": 534,
        "platform": "seatengine",
        "scraper_key": "seatengine",
        "source_url": "https://www.districtdome.com",
        "enabled": True,
    }
    if any(source.get(k) != v for k, v in pins.items()) or MARKER in (source.get("metadata") or {}):
        problems.append("Reviewed native source changed")
    shows = before["shows"]
    if len(shows) != 1 or shows[0].get("id") != 522028 or shows[0].get("club_id") != 554:
        problems.append("Reviewed show cohort changed")
    elif shows[0].get("show_page_url") != "https://www.districtdome.com/shows/291128" or shows[0].get("is_cancelled"):
        problems.append("Reviewed show provenance changed")
    tickets = [value for key, value in before["references"].items() if key.endswith(".tickets.show_id")]
    if len(tickets) != 1 or len(tickets[0]) != 11:
        problems.append("Expected eleven preserved ticket rows")
    if problems:
        raise ValueError("; ".join(problems))


def expected_after(before):
    result = deepcopy(before)
    club = result["club"][0]
    club.update(visible=False, club_type="non_comedy", description=DESCRIPTION)
    source = result["sources"][0]
    source["enabled"] = False
    source["metadata"] = dict(
        source.get("metadata") or {},
        **{
            MARKER: {
                "reason": "verified_non_comedy_and_mismatched_carry_on_inventory",
                "before_digest": digest(normalized(before)),
                "before_club_fields": {k: before["club"][0].get(k) for k in FIELDS},
                "before_source_enabled": True,
            }
        },
    )
    return result


def write_state(cur, state):
    club, source = state["club"][0], state["sources"][0]
    cur.execute("UPDATE clubs SET visible=%s,club_type=%s,description=%s WHERE id=554", tuple(club[k] for k in FIELDS))
    if cur.rowcount != 1:
        raise ValueError("Club disappeared")
    cur.execute(
        "UPDATE scraping_sources SET enabled=%s,metadata=%s::jsonb WHERE id=87 AND club_id=554",
        (source["enabled"], json.dumps(source["metadata"])),
    )
    if cur.rowcount != 1:
        raise ValueError("Source disappeared")


def repair(cur, before, backup_path=None):
    validate_before(before)
    refs = relationships(cur)
    actual = snapshot(cur, refs)
    expected = expected_after(before)
    if normalized(actual) == normalized(expected):
        return {"already_applied": True, "before": before, "after": actual}
    if normalized(actual) != normalized(before):
        raise ValueError("Before-image drift; review fresh evidence before writing")
    recovery = {"task_id": 4117, "before": before, "after": expected}
    if backup_path:
        save_backup(backup_path, recovery)
    write_state(cur, expected)
    after = snapshot(cur, refs)
    if normalized(after) != normalized(expected):
        raise ValueError("Preservation check failed; transaction must roll back")
    return {"already_applied": False, "before": before, "after": after}


def rollback(cur, recovery):
    if recovery.get("task_id") != 4117:
        raise ValueError("TASK-4117 recovery required")
    before = recovery["before"]
    validate_before(before)
    refs = relationships(cur)
    actual = snapshot(cur, refs)
    if normalized(actual) == normalized(before):
        return False
    if normalized(actual) != normalized(expected_after(before)):
        raise ValueError("After-state drift; refusing rollback")
    write_state(cur, before)
    if normalized(snapshot(cur, refs)) != normalized(before):
        raise ValueError("Rollback preservation check failed")
    return True


def summary(state):
    return {
        "club_id": state["club"][0]["id"],
        "visible": state["club"][0]["visible"],
        "enabled": state["sources"][0]["enabled"],
        "shows": len(state["shows"]),
        "references": {
            key: {"count": len(value), "sha256": digest(value)} for key, value in state["references"].items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--capture", type=Path)
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--rollback", type=Path)
    parser.add_argument("--before-file", type=Path)
    parser.add_argument("--backup-file", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup_file:
        parser.error("--apply requires --backup-file")
    if not args.capture and not args.rollback and not args.before_file:
        parser.error("--before-file required")
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    from laughtrack.adapters.db import get_transaction

    with get_transaction() as conn:
        with conn.cursor() as cur:
            if args.capture:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                before = snapshot(cur, relationships(cur, lock=False))
                validate_before(before)
                save_backup(args.capture, before)
                print(json.dumps({"PLAN_CAPTURE": summary(before)}))
            elif args.rollback:
                print(json.dumps({"rollback_changed": rollback(cur, json.loads(args.rollback.read_text()))}))
            else:
                result = repair(cur, json.loads(args.before_file.read_text()), args.backup_file if args.apply else None)
                print(
                    json.dumps(
                        {
                            "mode": "APPLY" if args.apply else "PLAN",
                            "already_applied": result["already_applied"],
                            "BEFORE": summary(result["before"]),
                            "AFTER": summary(result["after"]),
                        }
                    )
                )
        if not args.apply and not args.rollback:
            conn.rollback()
            print("PLAN: rolled back")
    if args.apply or args.rollback:
        print("COMMITTED: guarded District Dome disposition or restoration")


if __name__ == "__main__":
    main()
