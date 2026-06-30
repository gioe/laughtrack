#!/usr/bin/env python3
"""
Backfill shows.show_type for rows that have not been classified yet.

This script uses the same conservative classifier that the show write boundary
uses for new scraper output. Ambiguous rows are written as "unknown" so NULL
continues to mean "classification has not been attempted".

Usage:
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_show_type.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_show_type.py
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_show_type.py ARGS='--all-dates --limit 500'
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_connection
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.domain.show.classifier import classify_show_type


@dataclass(frozen=True)
class Candidate:
    show_id: int
    show_name: str
    description: str
    date: object
    club_id: int
    show_page_url: str
    tags: list[str]
    club_name: str
    club_website: str


def _fetch_candidates(*, all_dates: bool, limit: int | None) -> list[Candidate]:
    date_clause = "" if all_dates else "AND s.date >= NOW()"
    limit_clause = "LIMIT %s" if limit else ""
    params: tuple[int, ...] = (limit,) if limit else ()
    sql = f"""
        SELECT
            s.id,
            COALESCE(s.name, '') AS show_name,
            COALESCE(s.description, '') AS description,
            s.date,
            s.club_id,
            s.show_page_url,
            COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{{}}') AS tags,
            COALESCE(c.name, '') AS club_name,
            COALESCE(c.website, '') AS club_website
        FROM shows s
        JOIN clubs c ON c.id = s.club_id
        LEFT JOIN tagged_shows ts ON ts.show_id = s.id
        LEFT JOIN tags t ON t.id = ts.tag_id
        WHERE s.show_type IS NULL
        {date_clause}
        GROUP BY s.id, c.id
        ORDER BY s.id
        {limit_clause}
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [
                Candidate(
                    show_id=row[0],
                    show_name=row[1],
                    description=row[2],
                    date=row[3],
                    club_id=row[4],
                    show_page_url=row[5],
                    tags=list(row[6] or []),
                    club_name=row[7],
                    club_website=row[8],
                )
                for row in cur.fetchall()
            ]


def _classify_candidate(candidate: Candidate) -> str:
    date = candidate.date
    if getattr(date, "tzinfo", None) is not None:
        date = date.astimezone(timezone.utc)
    show = Show(
        name=candidate.show_name,
        description=candidate.description,
        date=date,
        club_id=candidate.club_id,
        show_page_url=candidate.show_page_url,
        supplied_tags=candidate.tags,
    )
    club = Club(
        id=candidate.club_id,
        name=candidate.club_name,
        address="",
        website=candidate.club_website,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )
    return classify_show_type(show, club=club)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill shows.show_type with the deterministic show type classifier."
    )
    parser.add_argument("--dry-run", action="store_true", help="Print classifications without writing.")
    parser.add_argument("--all-dates", action="store_true", help="Include past shows; default is future only.")
    parser.add_argument("--limit", type=int, help="Classify at most this many rows.")
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")

    candidates = _fetch_candidates(all_dates=args.all_dates, limit=args.limit)
    if not candidates:
        print("No unclassified show rows found.")
        return 0

    updates = [(candidate.show_id, _classify_candidate(candidate)) for candidate in candidates]
    counts: dict[str, int] = {}
    for _show_id, show_type in updates:
        counts[show_type] = counts.get(show_type, 0) + 1

    print(f"Classified {len(updates)} show rows.")
    print("Counts: " + ", ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    for show_id, show_type in updates[:10]:
        print(f"  [{show_id}] show_type={show_type}")
    if len(updates) > 10:
        print(f"  ... and {len(updates) - 10} more.")

    if args.dry_run:
        print("Dry run - no writes performed.")
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for show_id, show_type in updates:
                cur.execute(
                    "UPDATE shows SET show_type = %s WHERE id = %s AND show_type IS NULL",
                    (show_type, show_id),
                )
        conn.commit()

    print(f"Updated {len(updates)} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
