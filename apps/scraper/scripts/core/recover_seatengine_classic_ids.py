#!/usr/bin/env python3
"""
TASK-714: Recover correct seatengine_id for seatengine_classic clubs that were nulled
by the TASK-711 migration.

For each NULL-id seatengine_classic club, fetches the scraping_url HTML and extracts
the numeric SeatEngine venue ID from embedded CDN URLs
(files.seatengine.com/styles/logos/{ID}/...).

Since seatengine_classic uses scraping_url at runtime (not seatengine_id), this is
data-quality only — no scraping impact.

Usage:
    cd apps/scraper
    .venv/bin/python scripts/core/recover_seatengine_classic_ids.py
    .venv/bin/python scripts/core/recover_seatengine_classic_ids.py --dry-run
    .venv/bin/python scripts/core/recover_seatengine_classic_ids.py --club-id 42
"""

import argparse
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Optional

_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

from laughtrack.infrastructure.database.connection import get_transaction

load_dotenv(_repo_root / ".env")

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
    if "://" not in scraping_url:
        return "https://" + scraping_url
    return scraping_url


def _extract_seatengine_id_from_html(html: str) -> Optional[str]:
    matches = _SEATENGINE_CDN_RE.findall(html)
    if not matches:
        return None
    counts = Counter(matches)
    return counts.most_common(1)[0][0]


def _fetch_venue_id(club: dict, timeout: int = 20) -> Optional[str]:
    url = _build_url(club["scraping_url"])
    try:
        resp = requests.get(url, headers=_REQUESTS_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        return _extract_seatengine_id_from_html(resp.text)
    except Exception:
        return None


def _get_connection():
    return psycopg2.connect(
        dbname=os.environ.get("DATABASE_NAME", "neondb"),
        user=os.environ.get("DATABASE_USER", "neondb_owner"),
        host=os.environ.get("DATABASE_HOST", ""),
        password=os.environ.get("DATABASE_PASSWORD", ""),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        cursor_factory=psycopg2.extras.RealDictCursor,
        sslmode="require",
    )


def _fetch_clubs(conn, club_id: Optional[int] = None) -> list[dict]:
    with conn.cursor() as cur:
        if club_id:
            cur.execute(
                "SELECT id, name, scraping_url FROM clubs "
                "WHERE scraper = 'seatengine_classic' AND id = %s",
                (club_id,),
            )
        else:
            cur.execute(
                "SELECT id, name, scraping_url FROM clubs "
                "WHERE scraper = 'seatengine_classic' "
                "  AND (seatengine_id IS NULL OR seatengine_id = '') "
                "ORDER BY id"
            )
        return [dict(row) for row in cur.fetchall()]


def _update_seatengine_id(club_id: int, seatengine_id: str) -> None:
    with get_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clubs SET seatengine_id = %s WHERE id = %s",
                (seatengine_id, club_id),
            )


def main(dry_run: bool = False, club_id: Optional[int] = None) -> None:
    conn = _get_connection()
    clubs = _fetch_clubs(conn, club_id=club_id)
    label = f"(club_id={club_id})" if club_id else "with NULL seatengine_id"
    print(f"seatengine_classic clubs {label}: {len(clubs)}\n")

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
                _update_seatengine_id(club["id"], venue_id)
        else:
            print(
                f"{status} NO MATCH  id={club['id']:3d} '{club['name']:<42}'"
                f" ({club['scraping_url']})"
            )
            unmatched.append(club)

        if i < len(clubs):
            time.sleep(0.5)

    conn.close()

    print(f"\n{'─' * 70}")
    print(f"Matched  : {len(matched)}")
    print(f"Unmatched: {len(unmatched)}")

    if unmatched:
        print(f"\n⚠ {len(unmatched)} clubs could not be matched (investigate manually):")
        for c in unmatched:
            print(f"  id={c['id']:3d}  {c['name']:<45}  {c['scraping_url']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recover seatengine_id for nulled seatengine_classic clubs via HTML scrape"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    parser.add_argument("--club-id", type=int, help="Run for a single club ID only")
    args = parser.parse_args()
    main(dry_run=args.dry_run, club_id=args.club_id)
