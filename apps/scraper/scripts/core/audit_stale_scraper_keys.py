#!/usr/bin/env python3
"""
Repeatable check: enabled scraper keys have recent write activity.

Invariant
---------
Every distinct enabled ``scraping_sources.scraper_key`` should appear in
``shows.last_scraped_by`` with a non-null ``last_scraped_date`` inside the
configured lookback window. This catches enabled scraper configurations that
are no longer writing any shows, even if they still have old attribution rows.

Usage
-----
    cd apps/scraper
    make check-stale-scraper-keys
    make check-stale-scraper-keys ARGS='--days 14 --json'

Exits 0 when clean, 2 when stale keys are found, and 1 for execution/query
errors.
"""

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_connection


_STALE_KEYS_QUERY = """
    WITH enabled_keys AS (
        SELECT
            ss.scraper_key,
            COUNT(DISTINCT ss.club_id) AS enabled_source_count
        FROM scraping_sources ss
        WHERE ss.enabled = TRUE
          AND ss.scraper_key IS NOT NULL
          AND ss.scraper_key <> ''
        GROUP BY ss.scraper_key
    ),
    recent_activity AS (
        SELECT
            s.last_scraped_by AS scraper_key,
            COUNT(*) AS recent_show_count,
            MAX(s.last_scraped_date) AS most_recent_scrape
        FROM shows s
        WHERE s.last_scraped_by IS NOT NULL
          AND s.last_scraped_date IS NOT NULL
          AND s.last_scraped_date >= NOW() - (%s * INTERVAL '1 day')
        GROUP BY s.last_scraped_by
    )
    SELECT
        ek.scraper_key,
        ek.enabled_source_count,
        COALESCE(ra.recent_show_count, 0) AS recent_show_count,
        ra.most_recent_scrape
    FROM enabled_keys ek
    LEFT JOIN recent_activity ra ON ra.scraper_key = ek.scraper_key
    WHERE ra.scraper_key IS NULL
    ORDER BY ek.scraper_key
"""


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("--days must be at least 1")
    return parsed


def _fetch_stale_key_rows(days: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(_STALE_KEYS_QUERY, (days,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    return rows


def _format_row(row: dict[str, Any]) -> str:
    return (
        f"  scraper_key={row['scraper_key']!r} "
        f"enabled_sources={row['enabled_source_count']} "
        f"recent_shows={row['recent_show_count']} "
        f"most_recent_scrape={row.get('most_recent_scrape') or '-'}"
    )


def _print_human_report(rows: list[dict[str, Any]], *, days: int, stream=None) -> None:
    if stream is None:
        stream = sys.stdout
    if not rows:
        print(
            f"OK: Every enabled scraper_key has last_scraped_by activity in the last {days} day(s).",
            file=stream,
        )
        return

    print(
        f"ERROR: {len(rows)} enabled scraper_key value(s) have no "
        f"last_scraped_by activity in the last {days} day(s):",
        file=stream,
    )
    print(file=stream)
    for row in rows:
        print(_format_row(row), file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find enabled scraping_sources.scraper_key values with no recent "
            "shows.last_scraped_by activity. Exits 2 when stale keys are found, "
            "0 otherwise."
        )
    )
    parser.add_argument(
        "--days",
        type=_positive_int,
        default=7,
        help="Lookback window in days. Defaults to 7.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON document on stdout instead of the human-readable report.",
    )
    args = parser.parse_args(argv)

    try:
        rows = _fetch_stale_key_rows(args.days)
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        print(f"ERROR: failed to query stale scraper keys: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"days": args.days, "stale_scraper_keys": rows}, default=str, indent=2))
        _print_human_report(rows, days=args.days, stream=sys.stderr)
    else:
        _print_human_report(rows, days=args.days)

    return 2 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
