#!/usr/bin/env python3
"""Repair 16 reviewed Sesh location/schedule copies (TASK-4048).

Exact performance identities and dates were verified against the September 24
calendar and event detail pages. Different ticket URLs remain distinct. Three
other time-drift pairs are outside this bounded repair. No dates are shifted:
stale rows merge into existing source-verified canonical rows.

All seven show child tables are archived in a private recovery file; saved shows,
notifications and clicks are preserved. Canonical ticket/lineup/tag collisions
win; latest computed same-date feature snapshot wins per version/as_of identity.
Changed-date snapshots are archived because their features may be stale. Notification
collisions abort. Restore requires an exact post-repair state and stable schema.

Run from apps/scraper with PYTHONPATH=src:.:
  .venv/bin/python scripts/archive/repair_sesh_locations_2026_09_24.py --dry-run
  ... --apply --backup /private/tmp/task4048-recovery.json
  ... --restore /private/tmp/task4048-recovery.json
Recovery contains user data: never commit it. Default dry-run rolls back all rows;
PostgreSQL sequences can still advance. No automatic migration/deployment hook.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from psycopg2 import sql

MAPPING = {
    6029204: 6085451,
    3804632: 6085454,
    6029208: 6085455,
    6029209: 6085456,
    3804633: 6085457,
    3804634: 6085458,
    5916131: 6085459,
    5729638: 6085460,
    3804636: 6085461,
    3804637: 6085462,
    3804638: 6085463,
    6029206: 6085452,
    6085453: 6085452,
    6867495: 6085452,
    6670870: 6085452,
    6029205: 6670869,
}
EXPECTED = {
    3804632: {
        "name": "9/26 I Need This w/ Faith Ladzinski, Nick Tittone & Anderson Gronvold - 7:00 PM",
        "date": "2026-09-26 23:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=4NVM5GA4GAEIBDHWHH72PPEV",
    },
    3804633: {
        "name": "10/2 Hassan Phills - 7:00 PM",
        "date": "2026-10-02 23:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=Z7NVLZCJTKCQ6CMFO4H3AAM4",
    },
    3804634: {
        "name": "10/3 Hassan Phills - 7:00 PM",
        "date": "2026-10-03 23:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=K3UAYGXIY3NK3LYEXSNI7TX2",
    },
    3804636: {
        "name": "11/21 Dan Toomey & Industry Connections - 7:00 PM",
        "date": "2026-11-22 00:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=YAC36MNZFE7LEPLW5AYVRYCL",
    },
    3804637: {
        "name": "Saturday SESH Showcase 11/21",
        "date": "2026-11-22 01:30:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=2Y4GJQ5C5PHDB3M5CMD6CUV2",
    },
    3804638: {
        "name": "3/14 Late Sesh Showcase - 9:30 PM",
        "date": "2027-03-15 01:30:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=BSV2ZNJW3DJSCVB7WRPK7B6K",
    },
    5729638: {
        "name": "11/14 Daniela Mora - 7:00 PM",
        "date": "2026-11-15 00:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=2QNE5JYOPML2VPIMD6RXEFMH",
    },
    5916131: {
        "name": "11/12 Chris Higgins - 7:00 PM",
        "date": "2026-11-13 00:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=4MCZ6MAVAHBD5N3IWA43AHFV",
    },
    6029204: {
        "name": "9/24 Sienna Hubert-Ross - 7:00 PM",
        "date": "2026-09-24 23:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=FWI4R5LBKFB6JEX3C2QCGKDW",
    },
    6029205: {
        "name": "9/25 Friday Night SESH Showcase - 8:30 PM",
        "date": "2026-09-26 00:30:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=VKXCPHUZYZ3LCQ7HOVOR2LJC",
    },
    6029206: {
        "name": "9/25 Friday Night SESH Showcase - 10:00 PM",
        "date": "2026-09-26 02:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=K37YUZEWA5WKBHQGHIJ6JAKU",
    },
    6029208: {
        "name": "9/26 Saturday Night SESH Showcase - 8:30 PM",
        "date": "2026-09-27 00:30:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=QTZKDYZZYV3HUS7LMM2NCSWH",
    },
    6029209: {
        "name": "9/26 Saturday Night SESH Showcase - 10:00 PM",
        "date": "2026-09-27 02:00:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=5UHKPS6WXUFEZEZHWKIM4IP3",
    },
    6085451: {
        "name": "9/24 Sienna Hubert-Ross - 7:00 PM",
        "date": "2026-09-24 23:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=FWI4R5LBKFB6JEX3C2QCGKDW",
    },
    6085452: {
        "name": "9/25 Friday Night SESH Showcase - 8:30 PM",
        "date": "2026-09-26 00:30:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=K37YUZEWA5WKBHQGHIJ6JAKU",
    },
    6085453: {
        "name": "9/25 Friday Night SESH Showcase - 10:00 PM",
        "date": "2026-09-26 02:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=K37YUZEWA5WKBHQGHIJ6JAKU",
    },
    6085454: {
        "name": "9/26 I Need This w/ Faith Ladzinski, Nick Tittone & Anderson Gronvold - 7:00 PM",
        "date": "2026-09-26 23:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=4NVM5GA4GAEIBDHWHH72PPEV",
    },
    6085455: {
        "name": "9/26 Saturday Night SESH Showcase - 8:30 PM",
        "date": "2026-09-27 00:30:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=QTZKDYZZYV3HUS7LMM2NCSWH",
    },
    6085456: {
        "name": "9/26 Saturday Night SESH Showcase - 10:00 PM",
        "date": "2026-09-27 02:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=5UHKPS6WXUFEZEZHWKIM4IP3",
    },
    6085457: {
        "name": "10/2 Hassan Phills - 7:00 PM",
        "date": "2026-10-02 23:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=Z7NVLZCJTKCQ6CMFO4H3AAM4",
    },
    6085458: {
        "name": "10/3 Hassan Phills - 7:00 PM",
        "date": "2026-10-03 23:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=K3UAYGXIY3NK3LYEXSNI7TX2",
    },
    6085459: {
        "name": "11/12 Chris Higgins - 7:00 PM",
        "date": "2026-11-13 00:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=4MCZ6MAVAHBD5N3IWA43AHFV",
    },
    6085460: {
        "name": "11/14 Daniela Mora - 7:00 PM",
        "date": "2026-11-15 00:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=2QNE5JYOPML2VPIMD6RXEFMH",
    },
    6085461: {
        "name": "11/21 Dan Toomey & Industry Connections - 7:00 PM",
        "date": "2026-11-22 00:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=YAC36MNZFE7LEPLW5AYVRYCL",
    },
    6085462: {
        "name": "Saturday SESH Showcase 11/21",
        "date": "2026-11-22 01:30:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=2Y4GJQ5C5PHDB3M5CMD6CUV2",
    },
    6085463: {
        "name": "3/14 Late Sesh Showcase - 9:30 PM",
        "date": "2027-03-15 01:30:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=BSV2ZNJW3DJSCVB7WRPK7B6K",
    },
    6670869: {
        "name": "9/25 Friday Night SESH Showcase - 8:00 PM",
        "date": "2026-09-26 00:00:00+00:00",
        "room": "55 Chrystie - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=VKXCPHUZYZ3LCQ7HOVOR2LJC",
    },
    6670870: {
        "name": "9/25 Friday Night SESH Showcase - 9:30 PM",
        "date": "2026-09-26 01:30:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=K37YUZEWA5WKBHQGHIJ6JAKU",
    },
    6867495: {
        "name": "9/25 Friday Night SESH Showcase - 8:45 PM",
        "date": "2026-09-26 00:45:00+00:00",
        "room": "140 Eldridge - SESH Comedy",
        "show_page_url": "https://www.seshcomedy.com/event-detail.php?id=K37YUZEWA5WKBHQGHIJ6JAKU",
    },
}
CANONICAL_IDS = set(MAPPING.values())
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

    # These tables copy a reviewed list of columns. A new business field must
    # receive an explicit merge policy before this repair can run.
    for table, expected in {
        "tickets": {"id", "show_id", "purchase_url", "price", "sold_out", "type"},
        "lineup_items": {"id", "show_id", "comedian_id", "role"},
        "tagged_shows": {"id", "show_id", "tag_id"},
        "saved_shows": {"profile_id", "show_id", "created_at"},
    }.items():
        cur.execute(
            "SELECT attname FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped", (table,)
        )
        if {r[0] for r in cur.fetchall()} != expected:
            raise ValueError(f"{table} column shape changed; review merge policy")


def validate(cur, before):
    from datetime import datetime

    problems = []
    rows = {r["id"]: r for r in before["shows"]}
    for ident, expected in EXPECTED.items():
        row = rows.get(ident)
        if row is None and ident not in CANONICAL_IDS:
            continue
        if not row:
            problems.append(f"Canonical show {ident} changed or missing")
            continue
        if (
            (row["club_id"], row["last_scraped_by"]) != (16057, "fullcalendar_json")
            or any(row[key] != expected[key] for key in ("name", "room", "show_page_url"))
            or datetime.fromisoformat(row["date"]) != datetime.fromisoformat(expected["date"])
        ):
            problems.append(f"Reviewed show {ident} changed")
    cur.execute("SELECT city,state,timezone,address FROM clubs WHERE id=16057")
    if cur.fetchone() != ("New York", "NY", "America/New_York", "55 Chrystie St, New York, NY 10002, USA"):
        problems.append("Sesh club geography changed")
    cur.execute("SELECT club_id,platform,scraper_key,source_url FROM scraping_sources WHERE id=7653")
    if cur.fetchone() != (16057, "custom", "fullcalendar_json", "https://www.seshcomedy.com/feed.php"):
        problems.append("Sesh source identity changed")
    cur.execute(
        "SELECT id FROM shows WHERE club_id=16057 AND show_page_url=ANY(%s)",
        (list({v["show_page_url"] for v in EXPECTED.values()}),),
    )
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
        if EXPECTED[old]["date"] == EXPECTED[new]["date"]:
            # Same date/venue: retain the latest calculation per identity,
            # preserving the winning snapshot row ID and all its feature values.
            cur.execute(
                """DELETE FROM discovery_show_feature_snapshots loser USING
                discovery_show_feature_snapshots winner
                WHERE loser.show_id IN (%s,%s) AND winner.show_id IN (%s,%s)
                  AND loser.feature_version=winner.feature_version AND loser.as_of=winner.as_of
                  AND (loser.computed_at,loser.id)<(winner.computed_at,winner.id)""",
                (old, new, old, new),
            )
            cur.execute("UPDATE discovery_show_feature_snapshots SET show_id=%s WHERE show_id=%s", (new, old))
        # Changed-date feature snapshots remain in private recovery only; their
        # values may depend on the obsolete event date and must be recomputed.
        cur.execute("DELETE FROM shows WHERE id=%s", (old,))
        if cur.rowcount != 1:
            raise ValueError(f"Show {old} disappeared during repair")


def restore(cur, backup):
    if backup.get("task_id") != 4048 or backup.get("mapping") != {str(k): v for k, v in MAPPING.items()}:
        raise ValueError("Not a TASK-4048 recovery file")
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

    directory = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


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
                    "task_id": 4048,
                    "mapping": MAPPING,
                    "before": before,
                    "after": after,
                    "task_4048_dispositions": {
                        str(k): {"action": "merge", "canonical_show_id": v} for k, v in MAPPING.items()
                    },
                }
                save_backup(args.backup, payload)
            elif not args.restore:
                conn.rollback()
                print("DRY RUN: rolled back")


if __name__ == "__main__":
    main()
