#!/usr/bin/env python3
"""Reconcile source-reviewed AnyRoad blank rooms and duplicate slots (TASK-4135).

Background: legacy blank-room rows include source-proven duplicate placeholders.
What this does: merges five reviewed duplicates, corrects seven surviving slots,
and preserves all held inventory and relationships with exact guarded recovery.
Default is rolled-back dry run. Apply requires a new private backup; full JSON
recovery restores original show/child IDs only while the exact after-state holds.
Usage: --plan reviewed.json [--apply --backup /private/new.json], or
--plan reviewed.json --restore /private/new.json.after.json. Never commit backups.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from psycopg2 import sql
from scripts.core.repair_annoyance_identity import CHILDREN, save_backup
from scripts.core.repair_seatengine_organizer_venues import rows, digest, merge_show, CHILD_KEYS
from scripts.core.repair_next_stop_alberta_wall_times import lock_schema as base_lock_schema

CLUB_IDS = [10970, 61212]
MERGES = {3789152: 3179527, 3789159: 3179503, 3789169: 3179545, 3789163: 3179540, 3789171: 3179547}
ROOM_ONLY = {3558371, 3789139}
TABLES = ("clubs", "production_companies", "production_company_venues", "scraping_sources", "shows", *CHILDREN)
PATCH_FIELDS = {"date", "club_id", "room", "production_company_id", "scraped_by_organizer_id"}


def sorted_rows(items):
    return sorted(items, key=lambda row: json.dumps(row, sort_keys=True))


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp requires timezone")
    return result


def lock_schema(cur):
    schema = base_lock_schema(cur)
    for table in ("production_company_venues", "scraping_sources"):
        cur.execute(sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(sql.Identifier(table)))
        cur.execute(
            "SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum",
            (table,),
        )
        columns = cur.fetchall()
        cur.execute(
            "SELECT a.attname FROM pg_index i JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,ord) ON true JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum WHERE i.indrelid=%s::regclass AND i.indisprimary ORDER BY k.ord",
            (table,),
        )
        schema[table] = dict(columns=columns, primary=[row[0] for row in cur.fetchall()])
    return json.loads(json.dumps(schema))


def snapshot(cur):
    cur.execute("SET LOCAL TIME ZONE 'UTC'")
    shows = rows(cur, "shows", "club_id", CLUB_IDS)
    ids = [r["id"] for r in shows]
    state = dict(
        shows=shows,
        clubs=rows(cur, "clubs", "id", CLUB_IDS),
        production_companies=rows(cur, "production_companies", "id", [50]),
        production_company_venues=rows(cur, "production_company_venues", "production_company_id", [50]),
        scraping_sources=rows(cur, "scraping_sources", "club_id", CLUB_IDS),
    )
    state.update({table: rows(cur, table, "show_id", ids) for table in CHILDREN})
    return state


def validate_decisions(decisions, state):
    wanted = set(MERGES.values()) | ROOM_ONLY
    if {d["id"] for d in decisions} != wanted or len(decisions) != len(wanted):
        raise ValueError("Exact reviewed seven surviving occurrences required")
    shows = {r["id"]: r for r in state["shows"]}
    source = next((r for r in state["scraping_sources"] if r["id"] == 6820), None)
    if (
        not source
        or source["club_id"] != 10970
        or not source["enabled"]
        or source["metadata"].get("plugin_id") != "rozziesquaretheater"
    ):
        raise ValueError("AnyRoad source identity changed")
    if source["metadata"].get("anyroad_venue_routes", {}).get("producer_id") != 50:
        raise ValueError("Reviewed producer routing missing")
    if not state["production_companies"] or {r["id"] for r in state["clubs"]} != set(CLUB_IDS):
        raise ValueError("Reviewed venues or producer missing")
    for d in decisions:
        patch, original = d["patch"], shows[d["id"]]
        if not d.get("experience_id") or not d.get("reason") or not patch or set(patch) - PATCH_FIELDS:
            raise ValueError("Unreviewed decision or patch")
        if (
            patch.get("production_company_id") != 50
            or patch.get("scraped_by_organizer_id") != 50
            or not patch.get("room")
        ):
            raise ValueError("Reviewed room and producer required")
        target = dict(original, **patch)
        if target["club_id"] not in CLUB_IDS or not target["show_page_url"].startswith(
            "https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/"
        ):
            raise ValueError("Unexpected venue or booking URL")
        if (
            timestamp(target["date"]).astimezone(ZoneInfo("America/New_York")).date()
            != timestamp(original["date"]).astimezone(ZoneInfo("America/New_York")).date()
        ):
            raise ValueError("Unreviewed occurrence date change")
        old = d.get("merge_from")
        if d["id"] in ROOM_ONLY:
            if old is not None or set(patch) - {"room", "production_company_id", "scraped_by_organizer_id"}:
                raise ValueError("2027 occurrences permit room/producer correction only")
        elif MERGES.get(old) != d["id"]:
            raise ValueError("Unreviewed duplicate pair")
        else:
            duplicate = shows[old]
            if (
                duplicate.get("room") not in ("", None)
                or duplicate["club_id"] != 10970
                or duplicate["show_page_url"] != original["show_page_url"]
            ):
                raise ValueError("Duplicate identity drift")
            local = timestamp(duplicate["date"]).astimezone(ZoneInfo("America/New_York"))
            if (local.hour, local.minute, local.second) != (9, 0, 0) or local.date() != timestamp(
                target["date"]
            ).astimezone(ZoneInfo("America/New_York")).date():
                raise ValueError("Duplicate is not reviewed same-day placeholder")


def expected_after(before, decisions):
    result = copy.deepcopy(before)
    shows = {r["id"]: r for r in result["shows"]}
    retired = {d["merge_from"] for d in decisions if d.get("merge_from") is not None}
    targets = []
    for d in decisions:
        target = dict(shows[d["id"]], **d["patch"])
        target["date"] = timestamp(target["date"]).astimezone(ZoneInfo("UTC")).isoformat()
        key = (target["club_id"], timestamp(target["date"]), target.get("room") or "")
        if key in targets:
            raise ValueError("Reviewed destination collision")
        targets.append(key)
        for r in shows.values():
            if r["id"] not in retired | {d["id"]} and (r["club_id"], timestamp(r["date"]), r.get("room") or "") == key:
                raise ValueError("Live destination collision")
            if (
                r["id"] not in retired | {d["id"]}
                and target.get("source_performance_id")
                and (r["club_id"], r.get("source_performance_id"))
                == (target["club_id"], target["source_performance_id"])
            ):
                raise ValueError("Native identity collision")
        shows[d["id"]] = target
        old = d.get("merge_from")
        if old is None:
            continue
        for table in CHILDREN:
            keys = CHILD_KEYS.get(table)
            destination = [r for r in result[table] if r["show_id"] == d["id"]]
            merged = []
            for row in result[table]:
                if row["show_id"] != old:
                    merged.append(row)
                    continue
                collision = next((r for r in destination if keys and all(r.get(k) == row.get(k) for k in keys)), None)
                if collision:
                    if any(v != collision.get(k) for k, v in row.items() if k not in {"id", "show_id"}):
                        raise ValueError(f"Lossless merge conflict: {table}")
                else:
                    merged.append(dict(row, show_id=d["id"]))
            result[table] = sorted_rows(merged)
        del shows[old]
    result["shows"] = sorted_rows(shows.values())
    for club in result["clubs"]:
        club["total_shows"] = sum(r["club_id"] == club["id"] for r in result["shows"])
    return result


def build_plan(cur, decisions):
    lock_schema(cur)
    before = snapshot(cur)
    validate_decisions(decisions, before)
    after = expected_after(before, decisions)
    return dict(
        task_id=4135,
        decisions=decisions,
        expected_shows=before["shows"],
        before_hash=digest(before),
        after_hash=digest(after),
    )


def repair(cur, plan, backup_path=None):
    if plan.get("task_id") != 4135:
        raise ValueError("TASK-4135 reviewed plan required")
    schema = lock_schema(cur)
    before = snapshot(cur)
    if digest(before) == plan["after_hash"]:
        return dict(already_applied=True, before=before, after=before)
    if digest(before) != plan["before_hash"] or before["shows"] != plan["expected_shows"]:
        raise ValueError("Exact before-image drift")
    validate_decisions(plan["decisions"], before)
    expected = expected_after(before, plan["decisions"])
    if digest(expected) != plan["after_hash"]:
        raise ValueError("Reviewed after-image mismatch")
    backup = dict(task_id=4135, plan_hash=digest(plan), schema=schema, before=before, before_hash=digest(before))
    if backup_path:
        save_backup(backup_path, backup)
    for d in plan["decisions"]:
        if d.get("merge_from") is not None:
            merge_show(cur, d["merge_from"], d["id"])
        patch = d["patch"]
        cur.execute(
            sql.SQL("UPDATE shows SET {} WHERE id=%s").format(
                sql.SQL(",").join(sql.SQL("{}=%s").format(sql.Identifier(k)) for k in patch)
            ),
            [*patch.values(), d["id"]],
        )
        if cur.rowcount != 1:
            raise ValueError("Canonical occurrence disappeared")
    cur.execute(
        "UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=clubs.id) WHERE id=ANY(%s)", (CLUB_IDS,)
    )
    after = snapshot(cur)
    if after != expected:
        raise ValueError("Relationship or held inventory preservation failed")
    backup.update(after=after, after_hash=digest(after), already_applied=False)
    if backup_path:
        save_backup(str(backup_path) + ".after.json", backup)
    return backup


def restore(cur, plan, backup):
    if backup.get("task_id") != 4135 or backup.get("plan_hash") != digest(plan):
        raise ValueError("Recovery does not match reviewed plan")
    if lock_schema(cur) != backup["schema"]:
        raise ValueError("Schema changed since backup")
    if any(digest(backup[k]) != backup[k + "_hash"] for k in ("before", "after")):
        raise ValueError("Recovery checksum mismatch")
    current = snapshot(cur)
    if current == backup["before"]:
        return False
    if current != backup["after"]:
        raise ValueError("Affected after-state drift; refusing restore")
    for table in reversed(TABLES):
        keys = backup["schema"][table]["primary"]
        old_ids = {tuple(r[k] for k in keys) for r in backup["before"][table]}
        new_ids = {tuple(r[k] for k in keys) for r in backup["after"][table]}
        for ident in new_ids - old_ids:
            where = sql.SQL(" AND ").join(sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(k)) for k in keys)
            cur.execute(sql.SQL("DELETE FROM {} WHERE {}").format(sql.Identifier(table), where), ident)
    for table in TABLES:
        keys = backup["schema"][table]["primary"]
        old = {tuple(r[k] for k in keys): r for r in backup["before"][table]}
        new = {tuple(r[k] for k in keys): r for r in backup["after"][table]}
        for ident, row in old.items():
            if ident not in new:
                cur.execute(
                    sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s::jsonb)").format(
                        sql.Identifier(table), sql.Identifier(table)
                    ),
                    (json.dumps(row),),
                )
            elif row != new[ident]:
                columns = [k for k in row if k not in keys]
                assignments = sql.SQL(",").join(
                    sql.SQL("{}=r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in columns
                )
                where = sql.SQL(" AND ").join(
                    sql.SQL("t.{} IS NOT DISTINCT FROM r.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys
                )
                cur.execute(
                    sql.SQL("UPDATE {} t SET {} FROM jsonb_populate_record(NULL::{},%s::jsonb) r WHERE {}").format(
                        sql.Identifier(table), assignments, sql.Identifier(table), where
                    ),
                    (json.dumps(row),),
                )
    if snapshot(cur) != backup["before"]:
        raise ValueError("Restore failed exact preservation")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--restore", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a private --backup")
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    from laughtrack.adapters.db import get_transaction

    plan = json.loads(args.plan.read_text())
    with get_transaction() as conn:
        with conn.cursor() as cur:
            if args.restore:
                print(json.dumps(dict(restored=restore(cur, plan, json.loads(args.restore.read_text())))))
            else:
                result = repair(cur, plan, args.backup if args.apply else None)
                print(
                    json.dumps(
                        dict(
                            already_applied=result["already_applied"],
                            before={k: len(v) for k, v in result["before"].items()},
                            after={k: len(v) for k, v in result["after"].items()},
                        )
                    )
                )
        if not args.apply and not args.restore:
            conn.rollback()
            print("PLAN: rolled back")
    if args.apply or args.restore:
        print("COMMITTED: reviewed AnyRoad reconciliation")


if __name__ == "__main__":
    main()
