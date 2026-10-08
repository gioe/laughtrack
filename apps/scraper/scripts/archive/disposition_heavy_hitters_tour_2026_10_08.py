#!/usr/bin/env python3
"""Disposition the source-verified Heavy Hitters Tour event-label identity.

Background: four Greenville tour performances were linked to a label as a person.
What this script does: hides the exact existing identity and removes only four
reviewed lineup links, preserving all shows, tickets and historical references.
Usage: --identities-file before.json --associations-file associations.json
       [--dry-run | --apply --backup-file /private/path/new.json].
Rollback: --rollback /private/path/new.json.after.json requires exact after-state.
Private recovery files must never be committed. Dry runs roll back all changes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2 import sql
from scripts.archive.disposition_whiplash_performer_labels_2026_10_06 import (
    lock_schema as lock_identity_schema,
    sorted_rows,
    verify_preservation,
)
from scripts.core.repair_annoyance_identity import CHILDREN, same_value, save_backup
from scripts.core.repair_seatengine_organizer_venues import rows

TARGETS = {1936878: ("aa1d65a5844b25bda5016b1c8868c08b", "Heavy Hitters Tour")}
SHOW_IDS = {5775541, 5775542, 5775543, 5775544}
MARKER = "task_4134_tour_label"
CHANGED_FIELDS = {"visible", "block_reason", "block_added_at"}


def validate_evidence(identities, associations):
    if {row["comedian"]["id"] for row in identities} != set(TARGETS) or len(identities) != 1:
        raise ValueError("Expected exactly the one reviewed identity")
    reviewed = []
    for item in identities:
        row = item["comedian"]
        if (row["uuid"], row["name"]) != TARGETS[row["id"]] or row["parent_comedian_id"] is not None:
            raise ValueError("Reviewed identity/canonical mapping differs")
        if row["visible"] is not True:
            raise ValueError("Reviewed original visibility differs")
        for lineup in item["lineups"] or []:
            if lineup["comedian_id"] != row["uuid"]:
                raise ValueError("Lineup belongs to an unreviewed performer")
            reviewed.append(lineup)
    if len(reviewed) != 4 or len(associations) != 4:
        raise ValueError("Expected four reviewed relationships")
    if {(row["show_id"], row["comedian_id"]) for row in reviewed} != {
        (row["show_id"], row["uuid"]) for row in associations
    }:
        raise ValueError("Reviewed relationship/source evidence differs")
    if {r["show_id"] for r in associations} != SHOW_IDS:
        raise ValueError("Unexpected show cohort")
    for row in associations:
        if (row["comedian_id"], row["uuid"], row["comedian_name"], row["club_id"]) != (
            1936878,
            TARGETS[1936878][0],
            TARGETS[1936878][1],
            73,
        ):
            raise ValueError("Unexpected performer or club evidence")
        if not any(
            source
            == dict(
                source_id=32, platform="seatengine", seatengine_id=464, source_url="greenvillecomedyzone.com/events"
            )
            for source in row["sources"]
        ):
            raise ValueError("Expected Greenville SeatEngine source binding")
    return sorted_rows(reviewed)


def lock_schema(cur):
    references = lock_identity_schema(cur)
    cur.execute("""SELECT c.conrelid::regclass::text
        FROM pg_constraint c
        WHERE c.contype='f' AND c.confrelid='lineup_items'::regclass""")
    if cur.fetchall():
        raise ValueError("Unexpected lineup foreign-key dependents; review preservation")
    return references


def snapshot(cur, associations, references):
    uuids = [value[0] for value in TARGETS.values()]
    show_ids = sorted({row["show_id"] for row in associations})
    state = {
        "comedians": rows(cur, "comedians", "id", TARGETS),
        "target_lineups": rows(cur, "lineup_items", "comedian_id", uuids),
        "shows": rows(cur, "shows", "id", show_ids),
    }
    state.update({table: rows(cur, table, "show_id", show_ids) for table in CHILDREN})
    club_ids = {row["club_id"] for row in associations}
    state["clubs"] = rows(cur, "clubs", "id", club_ids)
    state["sources"] = rows(cur, "scraping_sources", "club_id", club_ids)
    real_ids = {row["comedian_id"] for row in state["lineup_items"]} - set(uuids)
    state["real_comedians"] = rows(cur, "comedians", "uuid", real_ids)
    state["other_references"] = {}
    for schema, table, column, target, _ in references:
        if table == "lineup_items":
            continue
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}=ANY(%s)").format(
                sql.Identifier(schema, table), sql.Identifier(column)
            ),
            (list(TARGETS) if target == "id" else uuids,),
        )
        state["other_references"][f"{schema}.{table}.{column}"] = sorted_rows(row[0] for row in cur.fetchall())
    return state


def validate_state(state, identities, associations, reviewed):
    originals = {row["comedian"]["id"]: row["comedian"] for row in identities}
    actual = {row["id"]: row for row in state["comedians"]}
    if set(actual) != set(TARGETS):
        raise ValueError("An identity disappeared")
    applied = all(
        actual[ident]["visible"] is False
        and actual[ident].get("block_reason") == MARKER
        and actual[ident].get("block_added_at")
        for ident in TARGETS
    )
    problems = []
    for ident, original in originals.items():
        row = actual[ident]
        allowed = CHANGED_FIELDS if applied else set()
        if any(not same_value(key, row.get(key), value) for key, value in original.items() if key not in allowed):
            problems.append(f"Comedian {ident} before-image drift")
    if state["target_lineups"] != ([] if applied else reviewed):
        problems.append("Target lineup cohort changed or new associations appeared")
    shows = {row["id"]: row for row in state["shows"]}
    clubs = {row["id"]: row for row in state["clubs"]}
    for association in associations:
        show = shows.get(association["show_id"])
        mapping = {
            "show_name": "name",
            "date": "date",
            "show_page_url": "show_page_url",
            "club_id": "club_id",
            "last_scraped_by": "last_scraped_by",
            "source_performance_id": "source_performance_id",
            "description": "description",
        }
        if show is None or any(
            not same_value(target, show.get(target), association[key]) for key, target in mapping.items()
        ):
            problems.append(f"Show {association['show_id']} identity/source drift")
            continue
        if clubs[show["club_id"]]["name"] != association["club_name"]:
            problems.append("Venue identity changed")
        sources = sorted_rows(
            {
                "source_id": row["id"],
                "platform": row["platform"],
                "seatengine_id": row["seatengine_id"],
                "source_url": row["source_url"],
            }
            for row in state["sources"]
            if row["club_id"] == show["club_id"]
        )
        if sources != sorted_rows(association["sources"]):
            problems.append("Source association changed")
    if problems:
        raise ValueError("; ".join(sorted(set(problems))))
    return applied


def disposition(cur, identities, associations, backup_path=None):
    reviewed = validate_evidence(identities, associations)
    references = lock_schema(cur)
    before = snapshot(cur, associations, references)
    if validate_state(before, identities, associations, reviewed):
        return dict(already_applied=True, before=before, after=before)
    recovery = dict(
        task_id=4134, identities=identities, associations=associations, references=references, before=before
    )
    if backup_path:
        save_backup(backup_path, recovery)
    cur.execute(
        "UPDATE comedians SET visible=false,block_reason=%s,block_added_at=CURRENT_TIMESTAMP WHERE id=ANY(%s)",
        (MARKER, list(TARGETS)),
    )
    if cur.rowcount != 1:
        raise ValueError("Visible identity cohort changed")
    for row in reviewed:
        cur.execute(
            "DELETE FROM lineup_items WHERE show_id=%s AND comedian_id=%s AND id=%s",
            (row["show_id"], row["comedian_id"], row["id"]),
        )
        if cur.rowcount != 1:
            raise ValueError("Reviewed lineup disappeared")
    after = snapshot(cur, associations, references)
    validate_state(after, identities, associations, reviewed)
    verify_preservation(before, after, reviewed)
    recovery.update(already_applied=False, after=after)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", recovery)
    return recovery


def rollback(cur, recovery):
    if recovery.get("task_id") != 4134 or "after" not in recovery:
        raise ValueError("Full TASK-4134 after-state recovery file required")
    reviewed = validate_evidence(recovery["identities"], recovery["associations"])
    references = lock_schema(cur)
    state = snapshot(cur, recovery["associations"], references)
    if state == recovery["before"]:
        return False
    if state != recovery["after"]:
        raise ValueError("Affected data changed since disposition; refusing rollback")
    for row in recovery["before"]["comedians"]:
        cur.execute(
            "UPDATE comedians SET visible=%s,block_reason=%s,block_added_at=%s WHERE id=%s",
            (row["visible"], row["block_reason"], row["block_added_at"], row["id"]),
        )
    for row in reviewed:
        cur.execute(
            "INSERT INTO lineup_items SELECT * FROM jsonb_populate_record(NULL::lineup_items,%s::jsonb)",
            (json.dumps(row),),
        )
    if snapshot(cur, recovery["associations"], references) != recovery["before"]:
        raise ValueError("Rollback did not reproduce exact original state")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identities-file", type=Path)
    parser.add_argument("--associations-file", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--rollback", type=Path)
    parser.add_argument("--backup-file", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup_file:
        parser.error("--apply requires --backup-file")
    if not args.rollback and not (args.identities_file and args.associations_file):
        parser.error("Disposition requires both reviewed evidence files")
    from dotenv import load_dotenv

    load_dotenv(_root / ".env")
    from laughtrack.adapters.db import get_transaction

    with get_transaction() as connection:
        with connection.cursor() as cur:
            if args.rollback:
                changed = rollback(cur, json.loads(args.rollback.read_text()))
                print(json.dumps({"mode": "rollback", "changed": changed}))
            else:
                result = disposition(
                    cur,
                    json.loads(args.identities_file.read_text()),
                    json.loads(args.associations_file.read_text()),
                    args.backup_file if args.apply else None,
                )
                print(
                    json.dumps(
                        {
                            "mode": "apply" if args.apply else "PLAN",
                            "already_applied": result["already_applied"],
                            "before_lineups": len(result["before"]["target_lineups"]),
                            "after_lineups": len(result["after"]["target_lineups"]),
                        }
                    )
                )
        if not args.apply and not args.rollback:
            connection.rollback()
            print("PLAN: rolled back")
    if args.apply or args.rollback:
        print("COMMITTED: guarded performer disposition or restoration")


if __name__ == "__main__":
    main()
