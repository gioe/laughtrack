#!/usr/bin/env python3
"""Hide three reviewed event labels and detach only their reviewed lineups.

Background: Grand Opening, Summer 2026 and Heavy Hitters were ingested as people.
What this script does: preserves all identities and references, hides the two still
visible labels, and removes forty reviewed lineup associations. Summer's existing
block metadata is unchanged. No aliases, global deny-list entries or shows change.
Usage: --identities-file before.json --associations-file associations.json
       [--dry-run | --apply --backup-file /private/path/new.json].
Rollback: --rollback /private/path/new.json.after.json restores only when the full
affected after-state still matches. Private recovery files must not be committed.
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
from scripts.core.repair_annoyance_identity import CHILDREN, same_value, save_backup
from scripts.core.repair_seatengine_organizer_venues import rows

TARGETS = {
    2353268: ("6e80add9cc5764dea961293da97a9a6e", "Grand Opening"),
    518570: ("2e49d77248f05d5b9c0fa6467dc50fea", "Summer 2026"),
    2447993: ("be88ca2bc26b2b43c28b7938d79cdbb8", "Heavy Hitters"),
}
MARKER = "task_4115_event_label"
CHANGED_FIELDS = {"visible", "block_reason", "block_added_at"}


def sorted_rows(values):
    return sorted(values, key=lambda row: json.dumps(row, sort_keys=True))


def validate_evidence(identities, associations):
    if {row["comedian"]["id"] for row in identities} != set(TARGETS) or len(identities) != 3:
        raise ValueError("Expected exactly the three reviewed identities")
    reviewed = []
    for item in identities:
        row = item["comedian"]
        if (row["uuid"], row["name"]) != TARGETS[row["id"]] or row["parent_comedian_id"] is not None:
            raise ValueError("Reviewed identity/canonical mapping differs")
        if row["visible"] is not (row["id"] != 518570):
            raise ValueError("Reviewed original visibility differs")
        for lineup in item["lineups"] or []:
            if lineup["comedian_id"] != row["uuid"]:
                raise ValueError("Lineup belongs to an unreviewed performer")
            reviewed.append(lineup)
    if len(reviewed) != 40 or len(associations) != 40:
        raise ValueError("Expected forty reviewed relationships")
    if {(row["show_id"], row["comedian_id"]) for row in reviewed} != {
        (row["show_id"], row["uuid"]) for row in associations
    }:
        raise ValueError("Reviewed relationship/source evidence differs")
    return sorted_rows(reviewed)


def lock_schema(cur):
    cur.execute("SET LOCAL lock_timeout='5s'; SET LOCAL TIME ZONE 'UTC'")
    cur.execute("LOCK TABLE comedians,shows IN SHARE ROW EXCLUSIVE MODE")
    cur.execute("""SELECT n.nspname,t.relname,a.attname,b.attname,array_length(c.conkey,1)
        FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1]
        JOIN pg_attribute b ON b.attrelid=c.confrelid AND b.attnum=c.confkey[1]
        WHERE c.contype='f' AND c.confrelid='comedians'::regclass""")
    references = cur.fetchall()
    if any(length != 1 or target not in {"uuid", "id"} for _, _, _, target, length in references):
        raise ValueError("Unexpected comedian foreign-key shape")
    tables = {(schema, table) for schema, table, _, _, _ in references}
    cur.execute(
        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(
            sql.SQL(",").join(
                [sql.Identifier(table) for table in ("clubs", "scraping_sources", *CHILDREN)]
                + [sql.Identifier(schema, table) for schema, table in sorted(tables)]
            )
        )
    )
    cur.execute(
        "SELECT c.conrelid::regclass::text,a.attname FROM pg_constraint c JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1] WHERE c.confrelid='shows'::regclass AND c.contype='f'"
    )
    if {(row[0].split(".")[-1].strip('"'), row[1]) for row in cur.fetchall()} != {
        (table, "show_id") for table in CHILDREN
    }:
        raise ValueError("Show relationship schema changed")
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
        if ident != 518570
    )
    problems = []
    for ident, original in originals.items():
        row = actual[ident]
        allowed = CHANGED_FIELDS if applied and ident != 518570 else set()
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


def verify_preservation(before, after, reviewed):
    for key in (
        "shows",
        "tickets",
        "clubs",
        "sources",
        "real_comedians",
        "other_references",
        *[table for table in CHILDREN if table != "lineup_items"],
    ):
        if before[key] != after[key]:
            raise ValueError(f"Unrelated data changed: {key}")
    expected = [row for row in before["lineup_items"] if row not in reviewed]
    if after["lineup_items"] != expected or after["target_lineups"]:
        raise ValueError("Lineup removal exceeded reviewed relationships")


def disposition(cur, identities, associations, backup_path=None):
    reviewed = validate_evidence(identities, associations)
    references = lock_schema(cur)
    before = snapshot(cur, associations, references)
    if validate_state(before, identities, associations, reviewed):
        return dict(already_applied=True, before=before, after=before)
    recovery = dict(
        task_id=4115, identities=identities, associations=associations, references=references, before=before
    )
    if backup_path:
        save_backup(backup_path, recovery)
    cur.execute(
        "UPDATE comedians SET visible=false,block_reason=%s,block_added_at=CURRENT_TIMESTAMP WHERE id=ANY(%s)",
        (MARKER, [ident for ident in TARGETS if ident != 518570]),
    )
    if cur.rowcount != 2:
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
    if recovery.get("task_id") != 4115 or "after" not in recovery:
        raise ValueError("Full TASK-4115 after-state recovery file required")
    reviewed = validate_evidence(recovery["identities"], recovery["associations"])
    references = lock_schema(cur)
    state = snapshot(cur, recovery["associations"], references)
    if state == recovery["before"]:
        return False
    if state != recovery["after"]:
        raise ValueError("Affected data changed since disposition; refusing rollback")
    for row in recovery["before"]["comedians"]:
        if row["id"] == 518570:
            continue
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
