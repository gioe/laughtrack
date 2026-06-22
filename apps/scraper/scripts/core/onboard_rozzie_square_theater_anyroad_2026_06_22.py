#!/usr/bin/env python3
"""
Onboard The Rozzie Square Theater (Roslindale, MA) via the generic ``anyroad``
scraper (TASK-3158).

Rozzie's Squarespace site is only the CMS — its real ticketed calendar is the
AnyRoad booking widget (``window.anyroad = new AnyRoad({plugin:{id:
'rozziesquaretheater'}})``). The generic ``anyroad`` scraper reads
``/plugins/api/v3/experiences?plugin_id=rozziesquaretheater`` and fans each
experience's inline schedule into one show per date. ``scraping_sources`` has no
``external_id`` column, so the plugin id is wired in ``metadata.plugin_id``
(``source_url`` carries the human-facing widget URL as a parse fallback).

Shared-building note: Rozzie (5 Basile St / 18 Corinth St) hosts resident
companies CSz Boston (ComedySportz®) and Riot Theater (Riot Improv). The AnyRoad
feed is the *whole* building's ticketed calendar — both residents' shows appear
in it — so onboarding Rozzie alone covers the trio. Do NOT separately onboard
CSz Boston / Riot Theater (no such clubs exist today; this keeps it that way).

Idempotent: re-running reuses the club (matched by google_place_id, then name)
and updates the existing ``anyroad`` source in place.

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/onboard_rozzie_square_theater_anyroad_2026_06_22.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/onboard_rozzie_square_theater_anyroad_2026_06_22.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

_SCRAPER_KEY = "anyroad"
# ScrapingPlatform enum has no 'anyroad' value; use 'custom' (same convention as
# playhouse_square / vbo_tickets). Dispatch is by scraper_key, not platform.
_PLATFORM = "custom"
_PLUGIN_ID = "rozziesquaretheater"
_WIDGET_URL = f"https://app.anyroad.com/i/plugin/{_PLUGIN_ID}"

_CLUB_NAME = "The Rozzie Square Theater"
_GOOGLE_PLACE_ID = "ChIJRVOdn8x-44kRtXtU9mgi-jE"
_CLUB_DEFAULTS = {
    "address": "5 Basile St, Roslindale, MA 02131",
    "website": "http://www.rozziesquaretheater.com/",
    "city": "Boston",
    "state": "MA",
    "timezone": "America/New_York",
}


def _ensure_club(cur: RealDictCursor, dry_run: bool, log: dict[str, Any]) -> int | None:
    cur.execute("SELECT id, name FROM clubs WHERE google_place_id = %s", (_GOOGLE_PLACE_ID,))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT id, name FROM clubs WHERE name = %s", (_CLUB_NAME,))
        row = cur.fetchone()
    if row:
        log["club"] = {"action": "exists", "id": row["id"], "name": row["name"]}
        return row["id"]
    if dry_run:
        log["club"] = {"action": "would_create", "name": _CLUB_NAME, **_CLUB_DEFAULTS}
        return None
    cur.execute(
        """
        INSERT INTO clubs (name, address, website, city, state, timezone, google_place_id, visible)
        VALUES (%s, %s, %s, %s, %s, %s, %s, true)
        RETURNING id
        """,
        (
            _CLUB_NAME,
            _CLUB_DEFAULTS["address"],
            _CLUB_DEFAULTS["website"],
            _CLUB_DEFAULTS["city"],
            _CLUB_DEFAULTS["state"],
            _CLUB_DEFAULTS["timezone"],
            _GOOGLE_PLACE_ID,
        ),
    )
    new_id = cur.fetchone()["id"]
    log["club"] = {"action": "created", "id": new_id, "name": _CLUB_NAME}
    return new_id


def _wire_source(cur: RealDictCursor, club_id: int, dry_run: bool) -> dict[str, Any]:
    metadata = {"plugin_id": _PLUGIN_ID}
    entry: dict[str, Any] = {"club_id": club_id, "plugin_id": _PLUGIN_ID}

    cur.execute(
        "SELECT id FROM scraping_sources WHERE club_id = %s AND scraper_key = %s",
        (club_id, _SCRAPER_KEY),
    )
    existing = cur.fetchone()
    entry["action"] = "update_existing" if existing else "insert"

    if dry_run:
        return entry

    if existing:
        cur.execute(
            """
            UPDATE scraping_sources
            SET platform = %s, source_url = %s, priority = 0, enabled = true,
                metadata = %s::jsonb, updated_at = NOW()
            WHERE id = %s
            """,
            (_PLATFORM, _WIDGET_URL, json.dumps(metadata), existing["id"]),
        )
        entry["source_id"] = existing["id"]
    else:
        cur.execute(
            """
            INSERT INTO scraping_sources
                (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
            VALUES (%s, %s, %s, %s, 0, true, %s::jsonb)
            RETURNING id
            """,
            (club_id, _PLATFORM, _SCRAPER_KEY, _WIDGET_URL, json.dumps(metadata)),
        )
        entry["source_id"] = cur.fetchone()["id"]
    return entry


def run(dry_run: bool) -> dict[str, Any]:
    log: dict[str, Any] = {
        "task_id": 3158,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
    }
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            club_id = _ensure_club(cur, dry_run, log)
            if club_id is None:
                log["source"] = {"skipped": "club not yet created (dry-run)"}
            else:
                log["source"] = _wire_source(cur, club_id, dry_run)
            if dry_run:
                conn.rollback()
    return log


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Onboard The Rozzie Square Theater via the anyroad scraper (TASK-3158)."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log = run(dry_run=args.dry_run)
    print(json.dumps(log, indent=2, sort_keys=True))
    if args.dry_run:
        print("DRY RUN: no database rows were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
