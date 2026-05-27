#!/usr/bin/env python3
"""
Backfill Comedy Connection SeatEngine public show URLs for TASK-2487.

Background
----------
Comedy Connection (club 217) uses SeatEngine venue 14. The SeatEngine venue API
currently returns ``website = '#'``; older scraper code accepted that invalid
value as a URL base and persisted ``#/shows/<seatengine_show_id>`` into
``shows.show_page_url`` and ``tickets.purchase_url``.

What this script does
---------------------
1. Validates the expected Comedy Connection club and enabled SeatEngine source.
2. Sets the source URL and metadata public show base to
   ``https://events.ricomedyconnection.com``.
3. Rewrites only club 217 show/ticket URLs shaped ``#/shows/<id>`` to the
   public SeatEngine show base.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/backfill_comedy_connection_seatengine_urls_2026_05_27.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/backfill_comedy_connection_seatengine_urls_2026_05_27.py
"""

import argparse
import json
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

_CLUB_ID = 217
_CLUB_NAME = "Comedy Connection"
_SEATENGINE_ID = "14"
_PUBLIC_SHOW_BASE = "https://events.ricomedyconnection.com"
_METADATA_KEY = "task_2487_public_show_base"


def _load_metadata(raw) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    if raw is None:
        return {}
    return dict(raw)


def _planned_url_count(cur, table: str) -> int:
    if table == "shows":
        cur.execute(
            """
            SELECT COUNT(*)
            FROM shows
            WHERE club_id = %s
              AND show_page_url LIKE '#/shows/%%'
            """,
            (_CLUB_ID,),
        )
    else:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM tickets t
            JOIN shows s ON s.id = t.show_id
            WHERE s.club_id = %s
              AND t.purchase_url LIKE '#/shows/%%'
            """,
            (_CLUB_ID,),
        )
    return int(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Comedy Connection SeatEngine URLs for TASK-2487.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name
                FROM clubs
                WHERE id = %s
                """,
                (_CLUB_ID,),
            )
            club = cur.fetchone()
            if not club:
                print(f"ABORT: club {_CLUB_ID} not found", file=sys.stderr)
                return 1
            if club[1] != _CLUB_NAME:
                print(
                    f"ABORT: club {_CLUB_ID} name is {club[1]!r}, expected {_CLUB_NAME!r}",
                    file=sys.stderr,
                )
                return 1

            cur.execute(
                """
                SELECT id, platform, scraper_key, seatengine_id, source_url, enabled, priority, metadata
                FROM scraping_sources
                WHERE club_id = %s
                  AND platform = 'seatengine'
                  AND seatengine_id::text = %s
                ORDER BY priority, id
                """,
                (_CLUB_ID, _SEATENGINE_ID),
            )
            sources = cur.fetchall()
            if len(sources) != 1:
                print(
                    f"ABORT: expected one club {_CLUB_ID} SeatEngine source "
                    f"with seatengine_id={_SEATENGINE_ID}, found {len(sources)}",
                    file=sys.stderr,
                )
                return 1

            source_id, platform, scraper_key, seatengine_id, source_url, enabled, priority, raw_meta = sources[0]
            problems = []
            if platform != "seatengine" or scraper_key != "seatengine":
                problems.append(f"source {source_id}: platform/scraper_key={platform}/{scraper_key}")
            if str(seatengine_id) != _SEATENGINE_ID:
                problems.append(f"source {source_id}: seatengine_id={seatengine_id}")
            if not enabled:
                problems.append(f"source {source_id}: enabled={enabled}")
            if priority != 0:
                problems.append(f"source {source_id}: priority={priority}")
            if problems:
                print("ABORT: shape mismatch:", file=sys.stderr)
                for problem in problems:
                    print(f"  {problem}", file=sys.stderr)
                return 1

            show_count = _planned_url_count(cur, "shows")
            ticket_count = _planned_url_count(cur, "tickets")
            metadata = _load_metadata(raw_meta)
            target_metadata = {
                **metadata,
                "public_show_base_url": _PUBLIC_SHOW_BASE,
                _METADATA_KEY: {
                    "kind": "seatengine_public_show_base",
                    "public_show_base_url": _PUBLIC_SHOW_BASE,
                    "replaces_invalid_venue_website": "#",
                },
            }

            print("=== BEFORE ===")
            print(f"  club={_CLUB_ID} source={source_id} seatengine_id={seatengine_id} " f"source_url={source_url!r}")
            print(f"  shows with #/shows URLs:   {show_count}")
            print(f"  tickets with #/shows URLs: {ticket_count}")
            print(f"  metadata public_show_base_url={metadata.get('public_show_base_url')!r}")

            source_needs_update = (
                source_url != _PUBLIC_SHOW_BASE
                or metadata.get("public_show_base_url") != _PUBLIC_SHOW_BASE
                or metadata.get(_METADATA_KEY) != target_metadata[_METADATA_KEY]
            )
            if not source_needs_update and show_count == 0 and ticket_count == 0:
                print("\nNo changes needed (idempotent re-run).")
                return 0

            if args.dry_run:
                print("\n--dry-run: no DB write performed.")
                return 0

            if source_needs_update:
                cur.execute(
                    """
                    UPDATE scraping_sources
                    SET source_url = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (_PUBLIC_SHOW_BASE, json.dumps(target_metadata, sort_keys=True), source_id),
                )

            cur.execute(
                """
                UPDATE shows
                SET show_page_url = %s || substring(show_page_url from 2)
                WHERE club_id = %s
                  AND show_page_url LIKE '#/shows/%%'
                """,
                (_PUBLIC_SHOW_BASE, _CLUB_ID),
            )
            updated_shows = cur.rowcount

            cur.execute(
                """
                UPDATE tickets t
                SET purchase_url = %s || substring(t.purchase_url from 2)
                FROM shows s
                WHERE s.id = t.show_id
                  AND s.club_id = %s
                  AND t.purchase_url LIKE '#/shows/%%'
                """,
                (_PUBLIC_SHOW_BASE, _CLUB_ID),
            )
            updated_tickets = cur.rowcount

            print("\n=== AFTER ===")
            print(f"  source updated: {source_needs_update}")
            print(f"  shows updated:  {updated_shows}")
            print(f"  tickets updated:{updated_tickets}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
