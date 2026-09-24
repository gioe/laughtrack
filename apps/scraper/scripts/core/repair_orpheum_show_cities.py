#!/usr/bin/env python3
"""Repair the eight verified stale Orpheum show copies (TASK-4047).

Background: historical name-only Ticketmaster venue matches left wrong-city and
wrong-time copies after venue identity was repaired. Canonical copies coexist.

What this script does: validates the exact cohort and venue identities, archives
every affected show and child row, repoints user references, and removes stale
copies. Conflicting notification identities fail closed. Feature snapshots for
wrong-city shows are archived, not reassigned to a different geographic context.
The private recovery file records complete before/after states and dispositions;
restore refuses if any affected row changed after repair. Do not commit that file
because it can contain user identifiers. No schema changes are needed.

Usage (from apps/scraper):
  PYTHONPATH=src:. .venv/bin/python scripts/core/repair_orpheum_show_cities.py --dry-run
  ... --apply --backup /private/tmp/task4047-recovery.json
  ... --restore /private/tmp/task4047-recovery.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from psycopg2 import sql

MAPPING = {
    3313105: 6897100,
    3399346: 6897100,
    2841348: 3398812,
    2841349: 3398813,
    2841350: 3398814,
    2841351: 3398815,
    2841352: 3398816,
    2841353: 3398817,
}
CANONICAL = {
    6897100: (
        27901,
        "2026-10-15T02:00:00+00:00",
        "https://www.etix.com/ticket/p/95654683/ilana-glazer-live-phoenix-orpheum-theatre-phoenix",
    ),
    3398812: (
        11385,
        "2026-09-20T02:00:00+00:00",
        "https://www.ticketmaster.com/comedy-bang-bang-ground-beefing-tour-los-angeles-california-09-19-2026/event/090064A6C1883E67",
    ),
    3398813: (
        11385,
        "2026-10-17T02:00:00+00:00",
        "https://www.ticketmaster.com/daniel-sloss-bitter-brand-new-tour-los-angeles-california-10-16-2026/event/09006444A54663CE",
    ),
    3398814: (
        11385,
        "2026-10-17T04:45:00+00:00",
        "https://www.ticketmaster.com/daniel-sloss-bitter-brand-new-tour-los-angeles-california-10-16-2026/event/09006391F491B2FB",
    ),
    3398815: (
        11385,
        "2026-10-18T03:00:00+00:00",
        "https://www.ticketmaster.com/laura-ramoso-the-calm-down-tour-los-angeles-california-10-17-2026/event/0900646C8A7D523C",
    ),
    3398816: (
        11385,
        "2026-10-25T03:00:00+00:00",
        "https://www.ticketmaster.com/george-lopez-los-angeles-california-10-24-2026/event/09006469F133DFAA",
    ),
    3398817: (
        11385,
        "2026-11-14T03:00:00+00:00",
        "https://www.ticketmaster.com/gianmarco-soresi-the-misery-loves-tour-los-angeles-california-11-13-2026/event/090064B69D06B47E",
    ),
}
VENUES = {
    2861: ("Minneapolis", "MN", "KovZpakSUe"),
    11385: ("Los Angeles", "CA", "KovZpa3uCe"),
    27901: ("Phoenix", "AZ", "ZFr9jZedA1"),
}
CHILDREN = (
    "tickets",
    "lineup_items",
    "tagged_shows",
    "sent_notifications",
    "ticket_purchase_click_events",
    "discovery_show_feature_snapshots",
    "saved_shows",
)
IDS = sorted(set(MAPPING) | set(MAPPING.values()))


def snapshot(cur):
    result = {}
    for table in ("shows", *CHILDREN):
        column = "id" if table == "shows" else "show_id"
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {} = ANY(%s)").format(
                sql.Identifier(table), sql.Identifier(column)
            ),
            (IDS,),
        )
        result[table] = sorted((r[0] for r in cur.fetchall()), key=lambda r: json.dumps(r, sort_keys=True))
    return result


def lock_and_validate_schema(cur):
    cur.execute("SET LOCAL lock_timeout = '5s'")
    # Short bounded operation. Block writers to both parent and children, so a
    # concurrent saved-show insertion cannot race the snapshot and CASCADE.
    cur.execute(
        sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(
            sql.SQL(", ").join(map(sql.Identifier, ("clubs", "scraping_sources", "shows", *CHILDREN)))
        )
    )
    cur.execute("SELECT conrelid::regclass::text FROM pg_constraint WHERE confrelid='shows'::regclass AND contype='f'")
    actual = {r[0].split(".")[-1].strip('"') for r in cur.fetchall()}
    if actual != set(CHILDREN):
        raise ValueError(f"Show child schema changed: {actual}; review recovery coverage first")


def validate(cur, before):
    problems = []
    rows = {r["id"]: r for r in before["shows"]}
    from datetime import datetime, timedelta

    for ident, (club, when, url) in CANONICAL.items():
        row = rows.get(ident)
        if (
            not row
            or (row["club_id"], row["show_page_url"], row["room"], row["last_scraped_by"])
            != (club, url, "", "ticketmaster_national")
            or datetime.fromisoformat(row["date"]) != datetime.fromisoformat(when)
        ):
            problems.append(f"Canonical show {ident} changed or missing")
    for old, new in MAPPING.items():
        row = rows.get(old)
        if row is None:  # already repaired
            continue
        expected_club = 11385 if old == 3399346 else 2861
        expected_date = datetime.fromisoformat(CANONICAL[new][1]) - timedelta(hours=0 if old == 3399346 else 2)
        if (row["club_id"], row["show_page_url"], row["room"], row["last_scraped_by"]) != (
            expected_club,
            CANONICAL[new][2],
            "",
            "ticketmaster_national",
        ) or datetime.fromisoformat(row["date"]) != expected_date:
            problems.append(f"Stale show {old} changed")
    for ident, (city, state, venue_id) in VENUES.items():
        cur.execute("SELECT city,state FROM clubs WHERE id=%s", (ident,))
        if cur.fetchone() != (city, state):
            problems.append(f"Venue {ident} geography changed")
        cur.execute(
            "SELECT club_id FROM scraping_sources WHERE platform='ticketmaster' AND ticketmaster_id=%s", (venue_id,)
        )
        if cur.fetchall() != [(ident,)]:
            problems.append(f"Ticketmaster venue {venue_id} identity changed")
    cur.execute("SELECT id FROM shows WHERE show_page_url=ANY(%s) ORDER BY id", ([v[2] for v in CANONICAL.values()],))
    if {r[0] for r in cur.fetchall()} != set(rows):
        problems.append("Additional copies exist outside the reviewed cohort")
    if problems:
        raise ValueError("; ".join(problems))


def repair(cur, before):
    present = {r["id"] for r in before["shows"]}
    for old, new in MAPPING.items():
        if old not in present:
            continue
        for table, columns, conflict in (
            ("lineup_items", "show_id,comedian_id,role", "(show_id,comedian_id)"),
            ("tagged_shows", "show_id,tag_id", "(show_id,tag_id)"),
            ("tickets", "show_id,purchase_url,price,sold_out,type", "(show_id,type)"),
        ):
            # Prefer current canonical commerce/lineup metadata on collisions.
            tail = columns.split(",", 1)[1]
            cur.execute(
                f"INSERT INTO {table} ({columns}) SELECT %s,{tail} FROM {table} WHERE show_id=%s ON CONFLICT {conflict} DO NOTHING",
                (new, old),
            )
        cur.execute(
            """INSERT INTO saved_shows (profile_id,show_id,created_at)
            SELECT profile_id,%s,created_at FROM saved_shows WHERE show_id=%s
            ON CONFLICT (profile_id,show_id) DO UPDATE SET created_at=LEAST(saved_shows.created_at,EXCLUDED.created_at)""",
            (new, old),
        )
        # Preserve notification IDs/grouping. A unique-key collision aborts the
        # transaction for explicit review instead of dropping delivery history.
        cur.execute("UPDATE sent_notifications SET show_id=%s WHERE show_id=%s", (new, old))
        cur.execute("UPDATE ticket_purchase_click_events SET show_id=%s WHERE show_id=%s", (new, old))
        cur.execute("DELETE FROM shows WHERE id=%s", (old,))
        if cur.rowcount != 1:
            raise ValueError(f"Show {old} disappeared during repair")


def restore(cur, backup):
    if backup.get("task_id") != 4047 or backup.get("mapping") != {str(k): v for k, v in MAPPING.items()}:
        raise ValueError("Not a TASK-4047 recovery file")
    live = snapshot(cur)
    if live == backup["before"]:
        return  # restore is idempotent
    if live != backup["after"]:
        raise ValueError("Affected data changed after repair; refusing automatic restore")
    validate(cur, live)
    for table in reversed(CHILDREN):
        cur.execute(sql.SQL("DELETE FROM {} WHERE show_id=ANY(%s)").format(sql.Identifier(table)), (IDS,))
    cur.execute("DELETE FROM shows WHERE id=ANY(%s)", (IDS,))
    for table in ("shows", *CHILDREN):
        for row in backup["before"][table]:
            cur.execute(
                sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{}, %s::jsonb)").format(
                    sql.Identifier(table), sql.Identifier(table)
                ),
                (json.dumps(row),),
            )
    if snapshot(cur) != backup["before"]:
        raise ValueError("Restore verification failed; rolling back")


def save_backup(path, payload):
    # Exclusive creation prevents overwriting the only recovery copy. File is
    # private and fsynced before the database transaction can commit.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def counts(state):
    return {table: len(rows) for table, rows in state.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--restore", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private --backup path")
    from dotenv import load_dotenv

    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    from laughtrack.adapters.db import get_transaction

    # get_transaction commits only on normal exit; dry-run explicitly rolls
    # back after validating the entire proposed mutation and post-state.
    with get_transaction() as conn:
        with conn.cursor() as cur:
            lock_and_validate_schema(cur)
            before = snapshot(cur)
            print("BEFORE " + json.dumps(counts(before), sort_keys=True))
            if args.restore:
                restore(cur, json.loads(args.restore.read_text()))
            else:
                validate(cur, before)
                repair(cur, before)
            after = snapshot(cur)
            if not args.restore:
                validate(cur, after)
            print("AFTER " + json.dumps(counts(after), sort_keys=True))
            if args.apply:
                payload = {
                    "task_id": 4047,
                    "mapping": MAPPING,
                    "before": before,
                    "after": after,
                    "task_4047_dispositions": {
                        str(k): {"action": "merge", "canonical_show_id": v} for k, v in MAPPING.items()
                    },
                }
                save_backup(args.backup, payload)
            elif not args.restore:
                conn.rollback()
                print("DRY RUN: rolled back")


if __name__ == "__main__":
    main()
