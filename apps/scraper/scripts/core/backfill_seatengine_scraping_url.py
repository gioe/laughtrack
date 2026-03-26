#!/usr/bin/env python3
"""
Backfill scraping_url for SeatEngine v1 clubs that still have the legacy
placeholder value 'www.seatengine.com'.

For each matching club, fetches GET /api/v1/venues/{seatengine_id} and updates
scraping_url with the real venue website URL returned by the API.

Idempotent: only touches clubs where scraping_url is still 'www.seatengine.com'.
Clubs that already have a real URL are left unchanged.

Usage:
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_seatengine_scraping_url.py
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_seatengine_scraping_url.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_seatengine_scraping_url.py ARGS='--club-id 84'
"""

import argparse
import os
import sys
import time
from typing import Optional

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import requests
from laughtrack.adapters.db import get_connection

_LEGACY_PLACEHOLDER = "www.seatengine.com"
_VENUES_API = "https://services.seatengine.com/api/v1/venues/{venue_id}"


def _build_headers(auth_token: str) -> dict:
    return {
        "x-auth-token": auth_token,
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
    }


def _fetch_clubs(club_id: Optional[int] = None) -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor()
        if club_id:
            cur.execute(
                "SELECT id, name, seatengine_id, scraping_url FROM clubs "
                "WHERE scraper = 'seatengine' AND seatengine_id IS NOT NULL "
                "AND seatengine_id != '' AND id = %s",
                (club_id,),
            )
        else:
            cur.execute(
                "SELECT id, name, seatengine_id, scraping_url FROM clubs "
                "WHERE scraper = 'seatengine' "
                "AND scraping_url = %s "
                "AND seatengine_id IS NOT NULL AND seatengine_id != '' "
                "ORDER BY id",
                (_LEGACY_PLACEHOLDER,),
            )
        rows = cur.fetchall()
        cur.close()
    return [
        {"id": r[0], "name": r[1], "seatengine_id": r[2], "scraping_url": r[3]}
        for r in rows
    ]


def _fetch_venue_website(seatengine_id: str, headers: dict, timeout: int = 15) -> Optional[str]:
    """Call GET /api/v1/venues/{seatengine_id} and return the website field."""
    url = _VENUES_API.format(venue_id=seatengine_id)
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None
        body = resp.json()
        data = body.get("data", body)
        website = (data.get("website") or "").strip().rstrip("/")
        return website if website else None
    except Exception:
        return None


def _update_scraping_url(club_id: int, scraping_url: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE clubs SET scraping_url = %s WHERE id = %s",
            (scraping_url, club_id),
        )
        conn.commit()
        cur.close()


def main(dry_run: bool = False, club_id: Optional[int] = None) -> None:
    auth_token = os.environ.get("SEATENGINE_AUTH_TOKEN", "")
    if not auth_token:
        print("ERROR: SEATENGINE_AUTH_TOKEN not set in .env")
        sys.exit(1)

    headers = _build_headers(auth_token)

    # When --club-id is given, fetch that club regardless of current scraping_url
    # so we can manually re-run for a specific club.  When running in bulk mode,
    # only fetch clubs still carrying the legacy placeholder (idempotent guard).
    clubs = _fetch_clubs(club_id=club_id)

    if not clubs:
        print("No clubs found matching the criteria — nothing to do.")
        return

    print(f"Clubs to backfill: {len(clubs)}\n")

    updated: list[dict] = []
    skipped: list[dict] = []  # API returned no website
    already_ok: list[dict] = []  # already has a real URL (only relevant in --club-id mode)

    for i, club in enumerate(clubs, 1):
        status = f"[{i:3d}/{len(clubs)}]"

        # In --club-id mode the club may already have a real scraping_url.
        if club["scraping_url"] != _LEGACY_PLACEHOLDER:
            print(
                f"{status} ALREADY OK  id={club['id']:3d}  '{club['name']}'  "
                f"scraping_url={club['scraping_url']}"
            )
            already_ok.append(club)
            continue

        website = _fetch_venue_website(club["seatengine_id"], headers)

        if website:
            print(
                f"{status} {'[DRY RUN] ' if dry_run else ''}"
                f"id={club['id']:3d}  '{club['name']:<42}'  → {website}"
            )
            updated.append(club)
            if not dry_run:
                _update_scraping_url(club["id"], website)
        else:
            print(
                f"{status} NO WEBSITE  id={club['id']:3d}  '{club['name']:<42}'  "
                f"(seatengine_id={club['seatengine_id']})"
            )
            skipped.append(club)

        if i < len(clubs):
            time.sleep(0.3)

    print(f"\n{'─' * 70}")
    print(f"Updated : {len(updated)}")
    print(f"Skipped : {len(skipped)}  (API returned no website)")
    if already_ok:
        print(f"Already OK: {len(already_ok)}")

    if skipped:
        print(f"\n⚠  {len(skipped)} clubs had no website in the API response (investigate manually):")
        for c in skipped:
            print(f"  id={c['id']:3d}  {c['name']:<45}  seatengine_id={c['seatengine_id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill scraping_url for SeatEngine v1 clubs using the SeatEngine venues API"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    parser.add_argument("--club-id", type=int, help="Run for a single club ID only")
    args = parser.parse_args()
    main(dry_run=args.dry_run, club_id=args.club_id)
