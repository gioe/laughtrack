#!/usr/bin/env python3
"""
Repeatable check: clubs with future shows must have enabled scrape config,
and active clubs must not be silently stuck on tour_dates after discovery.

Invariant 1 — orphan future inventory
-------------------------------------
Any club with future shows must have at least one enabled ``scraping_sources``
row. ``scraping_sources`` is the source of truth for per-platform scrape
configuration; future inventory without an enabled source usually means a stale
writer, legacy pre-source data, or a hidden duplicate row is still carrying
public listings.

Invariant 2 — stale tour_dates-only clubs
-----------------------------------------
``tour_dates`` (Bandsintown comedian-tour-date discovery) is a temporary
placeholder source: ``discover_clubs_from_tour_dates`` inserts a row when it
finds a new venue, and the expectation is that
``audit_tour_date_clubs --create-tasks`` then drives the venue onto a dedicated
scraper. Active clubs whose only enabled scraping_source is ``tour_dates`` for
longer than ``--stale-days`` (default 30) days indicate the discovery →
onboarding loop has rotted: either no audit has run, the resulting task was
never picked up, or the upgrade was never committed.

Usage
-----
    cd apps/scraper
    make check-scraping-source-invariants
    make check-scraping-source-invariants ARGS='--json'
    make check-scraping-source-invariants ARGS='--stale-days 14'

Exits 0 when clean, 2 when either invariant is violated (orphan future
inventory OR tour_dates-only clubs older than ``--stale-days``), and 1 for
execution/query errors. Tour_dates-only clubs younger than ``--stale-days``
are reported under a separate "recent discovery" section but do NOT trigger
exit 2 — they are the normal state of the discovery loop.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_connection


_ORPHAN_FUTURE_SHOWS_QUERY = """
    SELECT
        c.id AS club_id,
        c.name AS club_name,
        c.visible,
        c.status,
        COUNT(s.id) AS future_show_count,
        MIN(s.date) AS first_future_show,
        MAX(s.date) AS last_future_show,
        MIN(s.last_scraped_date) AS first_last_scraped_date,
        MAX(s.last_scraped_date) AS last_last_scraped_date,
        ARRAY_REMOVE(ARRAY_AGG(DISTINCT s.last_scraped_by), NULL) AS last_scraped_by_values,
        MIN(s.show_page_url) FILTER (WHERE s.show_page_url IS NOT NULL) AS sample_show_page_url
    FROM clubs c
    JOIN shows s ON s.club_id = c.id
    WHERE s.date > NOW()
      AND NOT EXISTS (
          SELECT 1
          FROM scraping_sources ss
          WHERE ss.club_id = c.id
            AND ss.enabled = TRUE
      )
    GROUP BY c.id, c.name, c.visible, c.status
    ORDER BY future_show_count DESC, c.id
"""


_TOUR_DATE_ONLY_CLUBS_QUERY = """
    WITH enabled_per_club AS (
        SELECT
            ss.club_id,
            BOOL_OR(ss.platform <> 'tour_dates') AS has_non_tour_date,
            MIN(ss.created_at) FILTER (WHERE ss.platform = 'tour_dates') AS tour_date_created_at
        FROM scraping_sources ss
        WHERE ss.enabled = TRUE
        GROUP BY ss.club_id
    )
    SELECT
        c.id AS club_id,
        c.name AS club_name,
        c.city,
        c.state,
        c.website,
        c.visible,
        c.status,
        epc.tour_date_created_at,
        (NOW()::date - epc.tour_date_created_at::date) AS tour_date_age_days
    FROM clubs c
    JOIN enabled_per_club epc ON epc.club_id = c.id
    WHERE epc.has_non_tour_date = FALSE
      AND epc.tour_date_created_at IS NOT NULL
      AND COALESCE(c.visible, TRUE) = TRUE
      AND c.status = 'active'
    ORDER BY tour_date_age_days DESC NULLS LAST, c.id
"""


def _fetch_orphan_future_show_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(_ORPHAN_FUTURE_SHOWS_QUERY)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    return rows


def _fetch_tour_date_only_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(_TOUR_DATE_ONLY_CLUBS_QUERY)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    return rows


def _classify_tour_date_rows(
    rows: list[dict[str, Any]], stale_days: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split tour_dates-only rows into (recent_discovery, onboarding_review_needed)."""
    recent: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    for row in rows:
        age = row.get("tour_date_age_days")
        classification = "onboarding_review_needed" if (age is not None and age > stale_days) else "recent_discovery"
        row["classification"] = classification
        (stale if classification == "onboarding_review_needed" else recent).append(row)
    return recent, stale


def _format_row(row: dict[str, Any]) -> str:
    values = ", ".join(row.get("last_scraped_by_values") or []) or "-"
    return (
        f"  club={row['club_id']} ({row['club_name']!r}, "
        f"visible={row['visible']}, status={row['status']}) "
        f"future_shows={row['future_show_count']} "
        f"last_scraped_by={values} "
        f"sample_url={row.get('sample_show_page_url') or '-'}"
    )


def _format_tour_date_row(row: dict[str, Any]) -> str:
    age = row.get("tour_date_age_days")
    age_str = f"{age}d" if age is not None else "?"
    return (
        f"  club={row['club_id']} ({row['club_name']!r}, "
        f"visible={row['visible']}, status={row['status']}) "
        f"tour_dates_age={age_str} "
        f"website={row.get('website') or '-'}"
    )


def _print_human_report(rows: list[dict[str, Any]], *, stream=None) -> None:
    if stream is None:
        stream = sys.stdout
    if not rows:
        print(
            "OK: No clubs have future shows without an enabled scraping_sources row.",
            file=stream,
        )
        return

    print(
        f"ERROR: {len(rows)} club(s) have future shows but no enabled "
        "scraping_sources row:",
        file=stream,
    )
    print(file=stream)
    for row in rows:
        print(_format_row(row), file=stream)


def _print_tour_date_report(
    recent: list[dict[str, Any]],
    stale: list[dict[str, Any]],
    stale_days: int,
    *,
    stream=None,
) -> None:
    if stream is None:
        stream = sys.stdout

    if not recent and not stale:
        print(
            "OK: No active clubs are stuck with only tour_dates as their enabled source.",
            file=stream,
        )
        return

    if stale:
        print(file=stream)
        print(
            f"ERROR: {len(stale)} active club(s) have only tour_dates enabled "
            f"and are older than {stale_days} days (onboarding review needed):",
            file=stream,
        )
        print(file=stream)
        for row in stale:
            print(_format_tour_date_row(row), file=stream)

    if recent:
        print(file=stream)
        print(
            f"INFO: {len(recent)} active club(s) have only tour_dates enabled "
            f"but are within {stale_days} days of discovery (normal):",
            file=stream,
        )
        print(file=stream)
        for row in recent:
            print(_format_tour_date_row(row), file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find clubs with future shows but no enabled scraping_sources row, "
            "and active clubs stuck on tour_dates-only sources after onboarding "
            "should have upgraded them. Exits 2 when either invariant is "
            "violated, 0 otherwise."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON document on stdout instead of the human-readable report.",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=30,
        help=(
            "Age (in days) above which a tour_dates-only club is flagged as "
            "needing onboarding review (default: 30)."
        ),
    )
    args = parser.parse_args(argv)

    if args.stale_days < 0:
        print("ERROR: --stale-days must be >= 0", file=sys.stderr)
        return 1

    try:
        orphan_rows = _fetch_orphan_future_show_rows()
        tour_date_rows = _fetch_tour_date_only_rows()
    except Exception as exc:
        print(f"ERROR: failed to query scraping source invariants: {exc}", file=sys.stderr)
        return 1

    recent_tour_date, stale_tour_date = _classify_tour_date_rows(tour_date_rows, args.stale_days)

    if args.json:
        payload = {
            "orphan_future_show_clubs": orphan_rows,
            "tour_date_only_clubs": {
                "stale_days_threshold": args.stale_days,
                "recent_discovery": recent_tour_date,
                "onboarding_review_needed": stale_tour_date,
            },
        }
        print(json.dumps(payload, default=str, indent=2))
        _print_human_report(orphan_rows, stream=sys.stderr)
        _print_tour_date_report(recent_tour_date, stale_tour_date, args.stale_days, stream=sys.stderr)
    else:
        _print_human_report(orphan_rows)
        _print_tour_date_report(recent_tour_date, stale_tour_date, args.stale_days)

    return 2 if (orphan_rows or stale_tour_date) else 0


if __name__ == "__main__":
    sys.exit(main())
