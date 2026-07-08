#!/usr/bin/env python3
"""
Repair stale Comedy Chateau SeatEngine ticket URLs.

Background
----------
Comedy Chateau tickets were persisted with SeatEngine API purchase URLs like
https://services.seatengine.com/api/v1/venues/417/shows/<id>. Those URLs are
authenticated API endpoints, not public buyer links. Venue id 417 is also not
Comedy Chateau in the SeatEngine API, so the iOS "Buy Tickets" button opens a
dead destination.

What this script does
---------------------
1. Adds scraping_sources.metadata.public_ticket_url for Comedy Chateau's primary
   SeatEngine source so future scrapes emit the public events page.
2. Rewrites existing Comedy Chateau ticket API URLs to that same public events
   page.
3. Corrects five stale Adele Givens tickets from Free to $25 based on
   authenticated SeatEngine inventory.

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/repair_comedy_chateau_seatengine_ticket_urls_2026_06_26.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/repair_comedy_chateau_seatengine_ticket_urls_2026_06_26.py
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

_CLUB_ID = 68
_SOURCE_ID = 118
_PUBLIC_TICKET_URL = "https://www.thecomedychateau.com/events"
_TASK_KEY = "task_2026_06_26_repair_seatengine_ticket_urls"
_PRICE_REPAIRS: dict[int, float] = {
    357101: 25.0,
    357102: 25.0,
    357103: 25.0,
    357104: 25.0,
    357105: 25.0,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair stale Comedy Chateau SeatEngine API ticket URLs.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, club_id, platform, scraper_key, source_url, seatengine_id, metadata, enabled, priority
                FROM scraping_sources
                WHERE id = %s
                """,
                (_SOURCE_ID,),
            )
            source = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*)
                FROM tickets t
                JOIN shows s ON s.id = t.show_id
                WHERE s.club_id = %s
                  AND t.purchase_url LIKE 'https://services.seatengine.com/api/%%'
                """,
                (_CLUB_ID,),
            )
            api_ticket_count = cur.fetchone()[0]

            cur.execute(
                """
                SELECT t.id, s.id, s.name, s.date, t.price, t.purchase_url
                FROM tickets t
                JOIN shows s ON s.id = t.show_id
                WHERE s.id = ANY(%s)
                ORDER BY s.date
                """,
                (list(_PRICE_REPAIRS.keys()),),
            )
            price_repair_rows = cur.fetchall()

        problems: list[str] = []
        if source is None:
            problems.append(f"missing scraping_sources id={_SOURCE_ID}")
        else:
            source_id, club_id, platform, scraper_key, source_url, seatengine_id, metadata, enabled, priority = source
            if club_id != _CLUB_ID:
                problems.append(f"source club_id={club_id} expected {_CLUB_ID}")
            if platform != "seatengine" or scraper_key != "seatengine":
                problems.append(f"source platform/scraper_key={platform}/{scraper_key} expected seatengine/seatengine")
            if source_url != "comedychateau.seatengine.com/events":
                problems.append(f"source_url={source_url!r} expected comedychateau.seatengine.com/events")
            if str(seatengine_id) != "432":
                problems.append(f"seatengine_id={seatengine_id!r} expected 432")
            if not enabled or priority != 0:
                problems.append(f"enabled={enabled} priority={priority} expected enabled=true priority=0")

        found_show_ids = {row[1] for row in price_repair_rows}
        missing_price_repair_ids = set(_PRICE_REPAIRS) - found_show_ids
        if missing_price_repair_ids:
            problems.append(f"missing price repair show ids: {sorted(missing_price_repair_ids)}")

        if problems:
            print("ABORT: shape mismatch, refusing to write:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1

        current_metadata = metadata or {}
        if isinstance(current_metadata, str):
            current_metadata = json.loads(current_metadata)
        existing_task_metadata = current_metadata.get(_TASK_KEY) if isinstance(current_metadata.get(_TASK_KEY), dict) else {}
        new_metadata = {
            **current_metadata,
            "public_ticket_url": _PUBLIC_TICKET_URL,
            _TASK_KEY: {
                "reason": "SeatEngine /shows/<id> redirects away for Comedy Chateau; API URLs are not public buyer links",
                "updated_ticket_count": existing_task_metadata.get("updated_ticket_count", api_ticket_count),
                "price_repair_show_ids": sorted(_PRICE_REPAIRS),
            },
        }

        print("=== BEFORE ===")
        print(f"source id={source_id} metadata={json.dumps(current_metadata, sort_keys=True)}")
        print(f"api ticket rows to rewrite: {api_ticket_count}")
        for ticket_id, show_id, name, date, price, purchase_url in price_repair_rows:
            print(f"  ticket={ticket_id} show={show_id} date={date} price={price} url={purchase_url}")

        if args.dry_run:
            print("\nDRY RUN: no changes written.")
            return 0

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scraping_sources
                SET metadata = %s::jsonb
                WHERE id = %s
                """,
                (json.dumps(new_metadata), _SOURCE_ID),
            )
            cur.execute(
                """
                UPDATE tickets t
                SET purchase_url = %s
                FROM shows s
                WHERE s.id = t.show_id
                  AND s.club_id = %s
                  AND t.purchase_url LIKE 'https://services.seatengine.com/api/%%'
                """,
                (_PUBLIC_TICKET_URL, _CLUB_ID),
            )
            updated_tickets = cur.rowcount
            updated_prices = 0
            for show_id, price in _PRICE_REPAIRS.items():
                cur.execute(
                    """
                    UPDATE tickets
                    SET price = %s
                    WHERE show_id = %s
                    """,
                    (price, show_id),
                )
                updated_prices += cur.rowcount

        print("\n=== AFTER ===")
        print(f"source id={source_id} metadata={json.dumps(new_metadata, sort_keys=True)}")
        print(f"updated ticket rows: {updated_tickets}")
        print(f"updated price rows: {updated_prices}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
