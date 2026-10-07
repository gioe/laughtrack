#!/usr/bin/env python3
"""Reconcile the reviewed Zarna Garg cancellation without deleting history.

Default: rollback-only dry run. --apply requires a new private --backup path.
Use --html with a freshly captured official detail page. --restore takes the
private backup and refuses intervening changes. Backup files contain user data.
"""

import argparse
import copy
import json
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from scripts.core.repair_annoyance_identity import CHILDREN, save_backup

SHOW_ID = 3092815
CLUB_ID = 9120
URL = "https://www.pabsttheatergroup.com/events/detail/zarna-garg-2026"


def snapshot(cur):
    result = {}
    for table in ("clubs", "shows", *CHILDREN):
        column = "id" if table in ("clubs", "shows") else "show_id"
        ident = CLUB_ID if table == "clubs" else SHOW_ID
        cur.execute(
            sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {}=%s").format(sql.Identifier(table), sql.Identifier(column)),
            (ident,),
        )
        result[table] = sorted((r[0] for r in cur.fetchall()), key=lambda r: json.dumps(r, sort_keys=True))
    return result


def lock(cur):
    cur.execute("SET LOCAL lock_timeout='3s'; SET LOCAL statement_timeout='10s'; SET LOCAL TIME ZONE 'UTC'")
    cur.execute("SELECT id FROM clubs WHERE id=%s FOR SHARE", (CLUB_ID,))
    cur.fetchall()
    cur.execute("SELECT id FROM shows WHERE id=%s OR show_page_url=%s ORDER BY id FOR UPDATE", (SHOW_ID, URL))
    if cur.fetchall() != [(SHOW_ID,)]:
        raise ValueError("Reviewed event cohort changed")
    cur.execute("SELECT conrelid::regclass::text FROM pg_constraint WHERE contype='f' AND confrelid='shows'::regclass")
    if {r[0].split(".")[-1].strip('"') for r in cur.fetchall()} != set(CHILDREN):
        raise ValueError("Show reference schema changed")
    for table in CHILDREN:
        cur.execute(sql.SQL("SELECT 1 FROM {} WHERE show_id=%s FOR UPDATE").format(sql.Identifier(table)), (SHOW_ID,))
        cur.fetchall()


def repair(conn, html, backup_path=None):
    from laughtrack.core.entities.show.handler import ShowHandler
    from laughtrack.scrapers.implementations.api.pabst_axs.cancellations import (
        extract_detail_identity,
        match_cancellation,
    )

    with conn.cursor() as cur:
        lock(cur)
        before = snapshot(cur)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT s.id,s.club_id,s.production_company_id,s.last_scraped_by,s.show_page_url,
            s.date,s.source_performance_id,s.name,c.name AS venue_name,c.address AS venue_address,c.zip_code AS venue_zip
            FROM shows s JOIN clubs c ON c.id=s.club_id WHERE s.id=%s""",
            (SHOW_ID,),
        )
        row = dict(cur.fetchone())
    if (
        row["club_id"],
        row["name"],
        row["venue_name"],
        row["venue_address"],
        row["venue_zip"],
        row["date"].isoformat(),
        row["production_company_id"],
        row["source_performance_id"],
    ) != (
        CLUB_ID,
        "ZARNA GARG: MILLION DOLLAR EXCUSES",
        "Turner Hall Ballroom",
        "1040 N Vel R. Phillips Ave",
        "53203",
        "2026-10-05T00:00:00+00:00",
        None,
        None,
    ):
        raise ValueError("Reviewed source or venue identity changed")
    intent = match_cancellation(extract_detail_identity(html, URL), [row], "pabst_theater_group", URL)
    if intent is None:
        raise ValueError("Official page does not corroborate reviewed cancellation")
    expected = copy.deepcopy(before)
    expected["shows"][0]["is_cancelled"] = True
    payload = dict(task_id=4125, before=before, after=expected)
    if backup_path:
        save_backup(backup_path, payload)
    ShowHandler().apply_cancellations([intent], conn=conn)
    with conn.cursor() as cur:
        if snapshot(cur) != expected:
            raise ValueError("Cancellation changed fields or references outside scope")
    if backup_path:
        save_backup(str(backup_path) + ".after.json", payload)
    return payload


def restore(conn, payload):
    if payload.get("task_id") != 4125:
        raise ValueError("Wrong repair backup")
    with conn.cursor() as cur:
        lock(cur)
        live = snapshot(cur)
        if live == payload["before"]:
            return
        if live != payload["after"]:
            raise ValueError("Affected state changed; refusing restore")
        cur.execute(
            "UPDATE shows SET is_cancelled=%s WHERE id=%s", (payload["before"]["shows"][0]["is_cancelled"], SHOW_ID)
        )
        if snapshot(cur) != payload["before"]:
            raise ValueError("Restore did not reproduce original state")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--restore", type=Path)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if not args.restore and (not args.html or (args.apply and not args.backup)):
        parser.error("--html is required; --apply also requires --backup")
    from dotenv import load_dotenv

    load_dotenv(_root / ".env")
    from laughtrack.adapters.db import get_transaction

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        if args.restore:
            restore(conn, json.loads(args.restore.read_text()))
        else:
            result = repair(conn, args.html.read_text(), args.backup if args.apply else None)
            print(
                json.dumps(
                    dict(
                        task_id=4125,
                        show_id=SHOW_ID,
                        applied=args.apply,
                        changed=result["before"] != result["after"],
                        child_counts={t: len(result["before"][t]) for t in CHILDREN},
                    )
                )
            )
            if not args.apply:
                restore(conn, result)
                conn.rollback()
                print("DRY RUN: repair and restore verified; rolled back")


if __name__ == "__main__":
    main()
