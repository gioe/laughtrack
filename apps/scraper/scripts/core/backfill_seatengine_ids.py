#!/usr/bin/env python3
"""
Backfill seatengine_id for clubs that have scraper='seatengine' but no seatengine_id.

For each club's scraping_url, fetches the events page HTML and extracts the numeric
SeatEngine venue ID from file CDN URLs (files.seatengine.com/styles/logos/{ID}/...).
Updates seatengine_id in the database for each match.

Usage:
    cd apps/scraper && python3 scripts/core/backfill_seatengine_ids.py
    python3 scripts/core/backfill_seatengine_ids.py --dry-run  # preview without writing
    python3 scripts/core/backfill_seatengine_ids.py --club-id 84  # single club
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import psycopg2
import psycopg2.extras
import requests

# ── SeatEngine venue ID extraction ──────────────────────────────────────────

# SeatEngine CDN URLs embed the numeric venue ID, e.g.:
#   files.seatengine.com/styles/logos/359/original/logo.png
#   files.seatengine.com/styles/header_images/359/full/banner.jpg
_SEATENGINE_CDN_RE = re.compile(
    r"files\.seatengine\.com/styles/(?:logos|header_images|favicons)/(\d+)/"
)

_REQUESTS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _build_url(scraping_url: str) -> str:
    """Ensure the scraping_url has an https:// prefix."""
    if "://" not in scraping_url:
        return "https://" + scraping_url
    return scraping_url


def _extract_seatengine_id_from_html(html: str) -> Optional[str]:
    """Return the first numeric SeatEngine venue ID found in CDN URLs."""
    matches = _SEATENGINE_CDN_RE.findall(html)
    if not matches:
        return None
    # Return the most-frequently occurring ID (in case of embedded widgets)
    from collections import Counter
    counts = Counter(matches)
    return counts.most_common(1)[0][0]


def _fetch_venue_id(club: dict, timeout: int = 20) -> Optional[str]:
    """
    Fetch the club's events page and extract the SeatEngine venue ID.
    Returns None if not found or request fails.
    """
    url = _build_url(club["scraping_url"])
    try:
        resp = requests.get(url, headers=_REQUESTS_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        return _extract_seatengine_id_from_html(resp.text)
    except Exception:
        return None


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_connection():
    return psycopg2.connect(
        dbname=os.environ.get("DATABASE_NAME", "neondb"),
        user=os.environ.get("DATABASE_USER", "neondb_owner"),
        host=os.environ.get("DATABASE_HOST", "ep-noisy-dew-amxl1zup.c-5.us-east-1.aws.neon.tech"),
        password=os.environ.get("DATABASE_PASSWORD", ""),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        cursor_factory=psycopg2.extras.RealDictCursor,
        sslmode="require",
    )


def _fetch_clubs_needing_id(conn, club_id: Optional[int] = None) -> list[dict]:
    with conn.cursor() as cur:
        if club_id:
            cur.execute(
                "SELECT id, name, scraping_url, website FROM clubs "
                "WHERE scraper = 'seatengine' AND id = %s",
                (club_id,),
            )
        else:
            cur.execute(
                "SELECT id, name, scraping_url, website FROM clubs "
                "WHERE scraper = 'seatengine' AND (seatengine_id IS NULL OR seatengine_id = '') "
                "ORDER BY id"
            )
        return [dict(row) for row in cur.fetchall()]


def _update_seatengine_id(conn, club_id: int, seatengine_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE clubs SET seatengine_id = %s WHERE id = %s",
            (seatengine_id, club_id),
        )
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, club_id: Optional[int] = None) -> None:
    conn = _get_connection()
    clubs = _fetch_clubs_needing_id(conn, club_id=club_id)
    print(f"Clubs needing seatengine_id: {len(clubs)}\n")

    matched: list[tuple[dict, str]] = []
    unmatched: list[dict] = []

    for i, club in enumerate(clubs, 1):
        venue_id = _fetch_venue_id(club)
        status = f"[{i:3d}/{len(clubs)}]"
        if venue_id:
            print(
                f"{status} {'[DRY RUN] ' if dry_run else ''}"
                f"id={club['id']:3d} '{club['name']:<42}' → seatengine_id={venue_id}"
            )
            matched.append((club, venue_id))
            if not dry_run:
                _update_seatengine_id(conn, club["id"], venue_id)
        else:
            print(f"{status} NO MATCH  id={club['id']:3d} '{club['name']:<42}' ({club['scraping_url']})")
            unmatched.append(club)

        # Polite delay between requests
        if i < len(clubs):
            time.sleep(0.5)

    conn.close()

    print(f"\n{'─'*70}")
    print(f"Matched  : {len(matched)}")
    print(f"Unmatched: {len(unmatched)}")

    if unmatched:
        print(f"\n⚠ {len(unmatched)} clubs could not be matched (investigate manually):")
        for c in unmatched:
            print(f"  id={c['id']:3d}  {c['name']:<45}  {c['scraping_url']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill seatengine_id for clubs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    parser.add_argument("--club-id", type=int, help="Run for a single club ID only")
    args = parser.parse_args()
    main(dry_run=args.dry_run, club_id=args.club_id)
