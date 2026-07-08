#!/usr/bin/env python3
"""
Onboard Playhouse Square (Cleveland) comedy via the dedicated playhouse_square
scraper (TASK-2942).

Playhouse Square is a multi-venue, multi-genre Tessitura operator that is NOT on
the WordPress tessi_production REST seam, so it cannot use the generic
``tessitura`` scraper. The new ``playhouse_square`` scraper reads the custom
carbonhouse ``events_ajax`` feed and isolates comedy by a known-comedian
heuristic, scoped to ONE theatre per source via ``metadata.venue_titles``.

Comedy at PHS lands across three theatres, so this script wires one
``playhouse_square`` source per theatre:
  - Connor Palace            -> club 5058 (canonical, post-dedupe)
  - Mimi Ohio Theatre        -> club 5394 (canonical, post-dedupe)
  - KeyBank State Theatre    -> created here (no club existed)

Per project policy (prefer the venue's own site over aggregators, to drive
ticket traffic to the box office), ``playhouse_square`` is wired at priority 0
and the existing ``ticketmaster_comedy`` source on each club is demoted to
priority 1 (kept as a fallback). The live partial unique index on
``(club_id, priority) WHERE enabled`` requires the demotion before the insert.

Idempotent: re-running updates the existing source's metadata in place and is a
no-op once ticketmaster_comedy is already demoted.

Usage:
    cd apps/scraper
    make run-script SCRIPT=scripts/core/onboard_playhouse_square_2026_06_17.py ARGS='--dry-run'
    make run-script SCRIPT=scripts/core/onboard_playhouse_square_2026_06_17.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
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

_FEED_URL = "https://www.playhousesquare.org/events"
_SCRAPER_KEY = "playhouse_square"
_PLATFORM = "custom"  # ScrapingPlatform enum has no playhouse_square value (convention).

_KEYBANK_NAME = "KeyBank State Theatre"
_KEYBANK_DEFAULTS = {
    "address": "1519 Euclid Ave, Cleveland, OH 44115",
    "website": "https://www.playhousesquare.org",
    "city": "Cleveland",
    "state": "OH",
    "timezone": "America/New_York",
}


@dataclass(frozen=True)
class VenueWiring:
    club_id: int | None        # None => resolved/created at runtime (KeyBank)
    label: str
    venue_titles: list[str]


def _ensure_keybank_club(cur: RealDictCursor, dry_run: bool, log: dict[str, Any]) -> int | None:
    cur.execute("SELECT id, visible FROM clubs WHERE name = %s", (_KEYBANK_NAME,))
    row = cur.fetchone()
    if row:
        log["keybank_club"] = {"action": "exists", "id": row["id"]}
        return row["id"]
    if dry_run:
        log["keybank_club"] = {"action": "would_create", "name": _KEYBANK_NAME, **_KEYBANK_DEFAULTS}
        return None
    cur.execute(
        """
        INSERT INTO clubs (name, address, website, city, state, timezone, visible)
        VALUES (%s, %s, %s, %s, %s, %s, true)
        RETURNING id
        """,
        (
            _KEYBANK_NAME,
            _KEYBANK_DEFAULTS["address"],
            _KEYBANK_DEFAULTS["website"],
            _KEYBANK_DEFAULTS["city"],
            _KEYBANK_DEFAULTS["state"],
            _KEYBANK_DEFAULTS["timezone"],
        ),
    )
    new_id = cur.fetchone()["id"]
    log["keybank_club"] = {"action": "created", "id": new_id}
    return new_id


def _wire_source(cur: RealDictCursor, club_id: int, venue_titles: list[str], dry_run: bool) -> dict[str, Any]:
    metadata = {"venue_titles": venue_titles}
    entry: dict[str, Any] = {"club_id": club_id, "venue_titles": venue_titles}

    cur.execute(
        "SELECT id, priority, enabled, metadata FROM scraping_sources "
        "WHERE club_id = %s AND scraper_key = %s",
        (club_id, _SCRAPER_KEY),
    )
    existing = cur.fetchone()

    # Demote any enabled ticketmaster_comedy source at priority 0 to priority 1
    # so playhouse_square can take priority 0 (prefer the venue's own site).
    cur.execute(
        "SELECT id FROM scraping_sources "
        "WHERE club_id = %s AND scraper_key = 'ticketmaster_comedy' AND priority = 0 AND enabled = true",
        (club_id,),
    )
    demote = cur.fetchone()
    entry["ticketmaster_comedy_demoted"] = bool(demote)

    if existing:
        entry["action"] = "update_existing"
        entry["source_id"] = existing["id"]
    else:
        entry["action"] = "insert"

    if dry_run:
        return entry

    if demote:
        cur.execute(
            "UPDATE scraping_sources SET priority = 1, updated_at = NOW() WHERE id = %s",
            (demote["id"],),
        )

    if existing:
        cur.execute(
            """
            UPDATE scraping_sources
            SET platform = %s, source_url = %s, priority = 0, enabled = true,
                metadata = %s::jsonb, updated_at = NOW()
            WHERE id = %s
            """,
            (_PLATFORM, _FEED_URL, json.dumps(metadata), existing["id"]),
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
            (club_id, _PLATFORM, _SCRAPER_KEY, _FEED_URL, json.dumps(metadata)),
        )
        entry["source_id"] = cur.fetchone()["id"]
    return entry


def run(dry_run: bool) -> dict[str, Any]:
    log: dict[str, Any] = {
        "task_id": 2942,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "sources": [],
    }
    wirings = [
        VenueWiring(club_id=5058, label="Connor Palace", venue_titles=["Connor Palace"]),
        VenueWiring(club_id=5394, label="Mimi Ohio Theatre", venue_titles=["Mimi Ohio Theatre"]),
        VenueWiring(club_id=None, label=_KEYBANK_NAME, venue_titles=[_KEYBANK_NAME]),
    ]

    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            keybank_id = _ensure_keybank_club(cur, dry_run, log)
            for w in wirings:
                club_id = w.club_id if w.club_id is not None else keybank_id
                if club_id is None:
                    log["sources"].append(
                        {"label": w.label, "skipped": "club not yet created (dry-run)"}
                    )
                    continue
                entry = _wire_source(cur, club_id, w.venue_titles, dry_run)
                entry["label"] = w.label
                log["sources"].append(entry)
            if dry_run:
                conn.rollback()
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description="Onboard Playhouse Square comedy via playhouse_square (TASK-2942).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log = run(dry_run=args.dry_run)
    print(json.dumps(log, indent=2, sort_keys=True))
    if args.dry_run:
        print("DRY RUN: no database rows were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
