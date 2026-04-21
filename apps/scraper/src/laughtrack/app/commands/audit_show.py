"""CLI command: audit-show

Performs a dry-run lineup comparison for a specific show.

Usage:
    python -m laughtrack.app.cli audit-show --show-id <N>

Steps:
1. Fetch the show's current lineup + club_id from the DB.
2. Look up the club's scraper key via club_id.
3. Run the club scraper in dry-run mode (no DB writes).
4. Match the show by (date, room) in the dry-run results.
5. Print a side-by-side diff: DB-only names, live-only names, names in both.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import List, Optional, Set

from laughtrack.adapters.db import db
from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_SHOW_SQL = """
SELECT
    s.id,
    s.date,
    s.room,
    s.name,
    s.club_id,
    cl.name  AS club_name,
    cl.address,
    cl.website,
    cl.popularity,
    cl.zip_code,
    cl.phone_number,
    cl.timezone,
    cl.visible,
    cl.city,
    cl.state,
    cl.status,
    cl.rate_limit,
    cl.max_retries,
    cl.timeout,
    COALESCE(
        json_agg(
            json_build_object(
                'id', ss.id,
                'club_id', ss.club_id,
                'platform', ss.platform,
                'scraper_key', ss.scraper_key,
                'external_id', ss.external_id,
                'source_url', ss.source_url,
                'priority', ss.priority,
                'enabled', ss.enabled,
                'metadata', COALESCE(ss.metadata, '{}'::jsonb)
            )
            ORDER BY ss.priority, ss.id
        ) FILTER (WHERE ss.id IS NOT NULL),
        '[]'::json
    ) AS scraping_sources
FROM shows s
JOIN clubs cl ON cl.id = s.club_id
LEFT JOIN scraping_sources ss ON ss.club_id = cl.id AND ss.enabled = TRUE
WHERE s.id = %s
GROUP BY
    s.id, s.date, s.room, s.name, s.club_id,
    cl.name, cl.address, cl.website, cl.popularity, cl.zip_code,
    cl.phone_number, cl.timezone, cl.visible, cl.city, cl.state,
    cl.status, cl.rate_limit, cl.max_retries, cl.timeout
"""

_LINEUP_SQL = """
SELECT co.name
FROM lineup_items li
JOIN comedians co ON co.uuid = li.comedian_id
WHERE li.show_id = %s
ORDER BY co.name
"""


def _fetch_show_and_club(show_id: int):
    """Return (show_row, db_lineup_names) or raise SystemExit on failure."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_SHOW_SQL, (show_id,))
            row = cur.fetchone()
            if row is None:
                print(f"Error: show ID {show_id} not found.", file=sys.stderr)
                sys.exit(1)

            # psycopg2 DictCursor or plain tuple — handle both
            if hasattr(row, "keys"):
                show_row = dict(row)
            else:
                cols = [d[0] for d in cur.description]
                show_row = dict(zip(cols, row))

            cur.execute(_LINEUP_SQL, (show_id,))
            db_lineup: List[str] = [r[0] for r in cur.fetchall()]

    return show_row, db_lineup


# ---------------------------------------------------------------------------
# Scraper dry-run
# ---------------------------------------------------------------------------

def _run_scraper_dry(club: Club) -> List[Show]:
    """Run the club's scraper and return the shows without writing to DB."""
    resolver = ScraperResolver()
    scraper_cls = resolver.get(club.scraper)  # type: ignore[arg-type]
    if scraper_cls is None:
        print(
            f"Error: no scraper registered for key '{club.scraper}' "
            f"(club: {club.name}).",
            file=sys.stderr,
        )
        sys.exit(1)

    scraper = scraper_cls(club)
    result = scraper.scrape_with_result()

    if result.error:
        print(f"Error: scraper failed — {result.error}", file=sys.stderr)
        sys.exit(1)

    return result.shows


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def _as_utc(dt: datetime) -> datetime:
    """Normalise a datetime to UTC, treating naive datetimes as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _match_show(
    target_date: datetime,
    target_room: str,
    scraped_shows: List[Show],
) -> Optional[Show]:
    """Return the first scraped show whose (date, room) matches the target.

    Matching strategy (in priority order):
    1. Exact UTC datetime + exact room (case-insensitive).
    2. Same calendar day (UTC) + exact room — handles small timezone rounding.
    """
    target_utc = _as_utc(target_date)
    target_room_norm = (target_room or "").strip().lower()

    # Pass 1: exact datetime match
    for show in scraped_shows:
        room_norm = (show.room or "").strip().lower()
        if _as_utc(show.date) == target_utc and room_norm == target_room_norm:
            return show

    # Pass 2: same calendar day + room
    target_day = target_utc.date()
    for show in scraped_shows:
        room_norm = (show.room or "").strip().lower()
        if _as_utc(show.date).date() == target_day and room_norm == target_room_norm:
            return show

    return None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _print_diff(
    show_id: int,
    show_name: str,
    show_date: datetime,
    room: str,
    club_name: str,
    db_names: List[str],
    live_names: List[str],
) -> None:
    db_set: Set[str] = {n.strip() for n in db_names}
    live_set: Set[str] = {n.strip() for n in live_names}

    only_db = sorted(db_set - live_set)
    only_live = sorted(live_set - db_set)
    in_both = sorted(db_set & live_set)

    utc_date = _as_utc(show_date)
    room_label = room or "(no room)"

    print("=" * 64)
    print(f"AUDIT SHOW #{show_id}: {show_name}")
    print(f"  Club  : {club_name}")
    print(f"  Date  : {utc_date.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Room  : {room_label}")
    print("=" * 64)

    if not db_names and not live_names:
        print("Both lineups are empty.")
        return

    if db_set == live_set:
        print(f"Lineups match ({len(in_both)} name(s)):")
        for name in in_both:
            print(f"  = {name}")
        return

    if in_both:
        print(f"In both ({len(in_both)}):")
        for name in in_both:
            print(f"  = {name}")

    if only_db:
        print(f"\nIn DB only ({len(only_db)}) — would be REMOVED by a re-scrape:")
        for name in only_db:
            print(f"  - {name}")

    if only_live:
        print(f"\nIn live scrape only ({len(only_live)}) — would be ADDED by a re-scrape:")
        for name in only_live:
            print(f"  + {name}")

    print()


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="audit-show",
        description=(
            "Dry-run lineup comparison: compares the DB lineup for a show "
            "against what the live scraper would return today."
        ),
    )
    parser.add_argument(
        "--show-id",
        type=int,
        required=True,
        metavar="N",
        help="Database ID of the show to audit.",
    )
    args = parser.parse_args(argv)
    show_id: int = args.show_id

    # 1. Fetch show + DB lineup
    show_row, db_lineup = _fetch_show_and_club(show_id)

    club_name: str = show_row.get("club_name", "")
    show_name: str = show_row.get("name", "")
    show_date: datetime = show_row["date"]
    room: str = show_row.get("room") or ""
    club_id: int = show_row["club_id"]
    club = Club.from_db_row(
        {
            "id": club_id,
            "name": club_name,
            "address": show_row.get("address", ""),
            "website": show_row.get("website", ""),
            "popularity": show_row.get("popularity", 0),
            "zip_code": show_row.get("zip_code", ""),
            "phone_number": show_row.get("phone_number", ""),
            "timezone": show_row.get("timezone", "America/New_York"),
            "city": show_row.get("city"),
            "state": show_row.get("state"),
            "visible": show_row.get("visible", True),
            "status": show_row.get("status", "active"),
            "rate_limit": show_row.get("rate_limit", 1.0),
            "max_retries": show_row.get("max_retries", 3),
            "timeout": show_row.get("timeout", 30),
            "scraping_sources": show_row.get("scraping_sources", []),
        }
    )
    club_scraper: Optional[str] = club.scraper

    # 2. Check scraper is configured
    if not club_scraper:
        print(
            f"Error: club '{club_name}' (id={club_id}) has no scraper configured.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 3. Reconstruct Club entity for the scraper
    print(
        f"Running scraper '{club_scraper}' for '{club_name}' (dry-run, no DB writes)...",
        flush=True,
    )

    # 4. Run scraper dry-run
    scraped_shows = _run_scraper_dry(club)
    print(f"Scraper returned {len(scraped_shows)} show(s).")

    # 5. Match show by (date, room)
    matched = _match_show(show_date, room, scraped_shows)

    if matched is None:
        utc_date = _as_utc(show_date)
        print(
            f"\nNo match found in live scrape for "
            f"date={utc_date.strftime('%Y-%m-%d %H:%M UTC')}, room='{room}'.",
            file=sys.stderr,
        )
        print("DB lineup:")
        if db_lineup:
            for name in sorted(db_lineup):
                print(f"  {name}")
        else:
            print("  (empty)")
        sys.exit(1)

    live_lineup = [c.name for c in matched.lineup]

    # 6. Print diff
    _print_diff(
        show_id=show_id,
        show_name=show_name,
        show_date=show_date,
        room=room,
        club_name=club_name,
        db_names=db_lineup,
        live_names=live_lineup,
    )


if __name__ == "__main__":
    main()
