#!/usr/bin/env python3
"""Move the reviewed New Hyde Park event without replacing its show ID (TASK-4124).

Run after the New Hyde Park venue migration. Default is rollback-only dry-run.
--apply requires a new private --backup path; --restore accepts that backup's
.after.json companion and refuses any affected-state drift. Backups contain
private user references and must not be committed. Only shows.club_id changes;
Los Angeles metadata and historical click attribution remain untouched.
"""

import argparse
import copy
import json
import sys
from decimal import Decimal
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2 import sql
from scripts.core.repair_annoyance_identity import CHILDREN, same_value, save_backup

SHOW_ID = 7123739
SOURCE_ID = 8828
URL = "https://www.nextstopcomedy.com/events/the-clubhouse-2026-10-24-8-pm"
SOURCE = dict(
    name="The Clubhouse",
    address="1607 N Vermont Ave, Los Angeles, CA 90027, USA",
    city="Los Angeles",
    state="CA",
    zip_code="90027",
    visible=False,
    website="https://www.instagram.com/theclubhouseimprovla",
    timezone="America/New_York",
)
TARGET = dict(
    name="The Clubhouse (New Hyde Park)",
    address="377 Denton Avenue",
    city="New Hyde Park",
    state="NY",
    zip_code="11040",
    country="US",
    timezone="America/New_York",
    website="https://www.theclubhouseny.com/",
    club_type="venue",
    visible=True,
    status="active",
)
SHOW = dict(
    id=SHOW_ID,
    date="2026-10-25T00:00:00+00:00",
    show_page_url=URL,
    last_scraped_by="next_stop_comedy",
    production_company_id=35,
    room="",
    source_performance_id=None,
    scraped_by_organizer_id=35,
    name="The Clubhouse",
    is_cancelled=False,
)


def matches(row, expected):
    return row is not None and all(same_value(k, row.get(k), v) for k, v in expected.items())


def lock_and_resolve(cur):
    cur.execute("SET LOCAL lock_timeout='3s'; SET LOCAL statement_timeout='10s'; SET LOCAL TIME ZONE 'UTC'")
    cur.execute("SELECT id FROM clubs WHERE id=%s OR name=%s ORDER BY id FOR UPDATE", (SOURCE_ID, TARGET["name"]))
    ids = [r[0] for r in cur.fetchall()]
    targets = [i for i in ids if i != SOURCE_ID]
    if SOURCE_ID not in ids or len(targets) != 1:
        raise ValueError("Expected source and exactly one migrated target venue")
    target = targets[0]
    cur.execute(
        "SELECT id FROM shows WHERE club_id=ANY(%s) OR id=%s OR show_page_url=%s ORDER BY id FOR UPDATE",
        (ids, SHOW_ID, URL),
    )
    cur.fetchall()
    cur.execute("SELECT id FROM club_aliases WHERE club_id=ANY(%s) ORDER BY id FOR UPDATE", (ids,))
    cur.fetchall()
    # No show or child is deleted. Keep the reference inventory explicit so a
    # newly introduced child table cannot silently escape recovery verification.
    cur.execute("SELECT conrelid::regclass::text FROM pg_constraint WHERE contype='f' AND confrelid='shows'::regclass")
    actual = {r[0].split(".")[-1].strip('"') for r in cur.fetchall()}
    if actual != set(CHILDREN):
        raise ValueError("Show reference schema changed")
    for table in CHILDREN:
        cur.execute(sql.SQL("SELECT 1 FROM {} WHERE show_id=%s FOR UPDATE").format(sql.Identifier(table)), (SHOW_ID,))
        cur.fetchall()
    return target


def snapshot(cur, target):
    state = {}
    for table in ("clubs", "club_aliases", "shows", *CHILDREN):
        if table == "clubs":
            where, args = "id=ANY(%s)", ([SOURCE_ID, target],)
        elif table == "club_aliases":
            where, args = "club_id=ANY(%s)", ([SOURCE_ID, target],)
        elif table == "shows":
            where, args = "club_id=ANY(%s) OR id=%s OR show_page_url=%s", ([SOURCE_ID, target], SHOW_ID, URL)
        else:
            where, args = "show_id=%s", (SHOW_ID,)
        cur.execute(sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE " + where).format(sql.Identifier(table)), args)
        state[table] = sorted((r[0] for r in cur.fetchall()), key=lambda row: json.dumps(row, sort_keys=True))
    return state


def validate(state, target):
    clubs = {r["id"]: r for r in state["clubs"]}
    if not matches(clubs.get(SOURCE_ID), SOURCE) or not matches(clubs.get(target), TARGET):
        raise ValueError("Source or target venue identity changed")
    aliases = [r for r in state["club_aliases"] if r["club_id"] == target and r["alias_name"] == "The Clubhouse"]
    if len(aliases) != 1 or not matches(
        aliases[0],
        dict(
            city="New Hyde Park",
            state="NY",
            verified=True,
            normalized_alias_name="the clubhouse",
            normalized_city="new hyde park",
            normalized_state="ny",
            source="TASK-4124",
        ),
    ):
        raise ValueError("Target alias evidence changed")
    rows = {r["id"]: r for r in state["shows"]}
    show = rows.get(SHOW_ID)
    if not matches(show, SHOW) or show["club_id"] not in (SOURCE_ID, target):
        raise ValueError("Reviewed show source evidence changed")
    tickets = state["tickets"]
    if (
        len(tickets) != 1
        or not matches(
            tickets[0], dict(id=8110440, show_id=SHOW_ID, type="General Admission", purchase_url=URL, sold_out=False)
        )
        or Decimal(str(tickets[0]["price"])) != Decimal("27")
    ):
        raise ValueError("Reviewed ticket evidence changed")
    for other in rows.values():
        if other["id"] != SHOW_ID and (
            other.get("show_page_url") == URL
            or (
                other["club_id"] == target
                and same_value("date", other.get("date"), SHOW["date"])
                and other.get("room") in (None, "")
            )
        ):
            raise ValueError("Target event or physical slot collision")
    return show["club_id"] == target


def repair(cur, backup_path=None):
    target = lock_and_resolve(cur)
    before = snapshot(cur, target)
    applied = validate(before, target)
    expected = copy.deepcopy(before)
    next(r for r in expected["shows"] if r["id"] == SHOW_ID)["club_id"] = target
    expected["shows"].sort(key=lambda row: json.dumps(row, sort_keys=True))
    payload = dict(task_id=4124, target_id=target, before=before, after=expected)
    if backup_path:
        save_backup(backup_path, payload)
    if not applied:
        cur.execute("UPDATE shows SET club_id=%s WHERE id=%s AND club_id=%s", (target, SHOW_ID, SOURCE_ID))
        if cur.rowcount != 1:
            raise ValueError("Show changed during repair")
    if snapshot(cur, target) != expected:
        raise ValueError("Repair changed fields outside the reviewed venue reassignment")
    if backup_path:
        save_backup(str(backup_path) + ".after.json", payload)
    return payload


def restore(cur, backup):
    if backup.get("task_id") != 4124:
        raise ValueError("Wrong repair backup")
    target = lock_and_resolve(cur)
    if target != backup["target_id"]:
        raise ValueError("Target changed since backup")
    live = snapshot(cur, target)
    if live == backup["before"]:
        return
    if live != backup["after"]:
        raise ValueError("Affected state changed; refusing restore")
    validate(live, target)
    original = next(r for r in backup["before"]["shows"] if r["id"] == SHOW_ID)
    cur.execute("UPDATE shows SET club_id=%s WHERE id=%s", (original["club_id"], SHOW_ID))
    if snapshot(cur, target) != backup["before"]:
        raise ValueError("Restore failed to reproduce the exact original state")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--restore", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private --backup path")
    from dotenv import load_dotenv

    load_dotenv(_root / ".env")
    from laughtrack.adapters.db import get_transaction

    with get_transaction() as connection:
        with connection.cursor() as cur:
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            if args.restore:
                restore(cur, json.loads(args.restore.read_text()))
                print("Restored reviewed venue assignment")
            else:
                result = repair(cur, args.backup if args.apply else None)
                print(
                    json.dumps(
                        dict(
                            task_id=4124,
                            show_id=SHOW_ID,
                            target_id=result["target_id"],
                            changed=result["before"] != result["after"],
                            applied=args.apply,
                        )
                    )
                )
                if not args.apply:
                    connection.rollback()
                    print("DRY RUN: rolled back")


if __name__ == "__main__":
    main()
