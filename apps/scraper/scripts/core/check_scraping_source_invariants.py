#!/usr/bin/env python3
"""
Repeatable check: clubs with future shows must have enabled scrape config,
and active clubs must not silently sit without any enabled scraper at all.

Invariant 1 — orphan future inventory
-------------------------------------
Any club with future shows must have at least one enabled ``scraping_sources``
row. ``scraping_sources`` is the source of truth for per-platform scrape
configuration; future inventory without an enabled source usually means a stale
writer, legacy pre-source data, or a hidden duplicate row is still carrying
public listings.

Invariant 2 — active clubs missing a scraper
--------------------------------------------
Any club whose ``status='active'`` and ``visible`` is true must have at least
one enabled ``scraping_sources`` row. An active venue with no enabled source
cannot ingest new inventory: either a dedicated scraper was never wired up
after onboarding, or every previously enabled source has since been disabled
without the club itself being deactivated. Invariant 1 already covers the
subset that still has future shows on the books; this invariant catches the
quieter case where the club has no future inventory yet (or anymore) and would
otherwise drift unscraped without a paging signal.

Usage
-----
    cd apps/scraper
    make check-scraping-source-invariants
    make check-scraping-source-invariants ARGS='--json'

Exits 0 when clean, 2 when either invariant is violated (orphan future
inventory OR active clubs missing a scraper), and 1 for execution/query
errors.
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


_ACTIVE_NO_SOURCE_QUERY = """
    SELECT
        c.id AS club_id,
        c.name AS club_name,
        c.city,
        c.state,
        c.website,
        c.visible,
        c.status
    FROM clubs c
    WHERE c.status = 'active'
      AND COALESCE(c.visible, TRUE) = TRUE
      AND NOT EXISTS (
          SELECT 1
          FROM scraping_sources ss
          WHERE ss.club_id = c.id
            AND ss.enabled = TRUE
      )
      AND NOT EXISTS (
          SELECT 1
          FROM shows s
          WHERE s.club_id = c.id
            AND s.date > NOW()
      )
    ORDER BY c.id
"""


def _fetch_orphan_future_show_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(_ORPHAN_FUTURE_SHOWS_QUERY)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    return rows


def _fetch_active_no_source_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(_ACTIVE_NO_SOURCE_QUERY)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    return rows


def _format_row(row: dict[str, Any]) -> str:
    values = ", ".join(row.get("last_scraped_by_values") or []) or "-"
    return (
        f"  club={row['club_id']} ({row['club_name']!r}, "
        f"visible={row['visible']}, status={row['status']}) "
        f"future_shows={row['future_show_count']} "
        f"last_scraped_by={values} "
        f"sample_url={row.get('sample_show_page_url') or '-'}"
    )


def _format_active_no_source_row(row: dict[str, Any]) -> str:
    return (
        f"  club={row['club_id']} ({row['club_name']!r}, "
        f"visible={row['visible']}, status={row['status']}) "
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


def _print_active_no_source_report(
    rows: list[dict[str, Any]],
    *,
    stream=None,
) -> None:
    if stream is None:
        stream = sys.stdout

    if not rows:
        print(
            "OK: No active clubs are missing an enabled scraping_sources row.",
            file=stream,
        )
        return

    print(file=stream)
    print(
        f"ERROR: {len(rows)} active club(s) have no enabled scraping_sources row:",
        file=stream,
    )
    print(file=stream)
    for row in rows:
        print(_format_active_no_source_row(row), file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find clubs with future shows but no enabled scraping_sources row, "
            "and active clubs missing an enabled scraping_sources row entirely. "
            "Exits 2 when either invariant is violated, 0 otherwise."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON document on stdout instead of the human-readable report.",
    )
    args = parser.parse_args(argv)

    try:
        orphan_rows = _fetch_orphan_future_show_rows()
        active_no_source_rows = _fetch_active_no_source_rows()
    except Exception as exc:
        print(f"ERROR: failed to query scraping source invariants: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = {
            "orphan_future_show_clubs": orphan_rows,
            "active_no_source_clubs": active_no_source_rows,
        }
        print(json.dumps(payload, default=str, indent=2))
        _print_human_report(orphan_rows, stream=sys.stderr)
        _print_active_no_source_report(active_no_source_rows, stream=sys.stderr)
    else:
        _print_human_report(orphan_rows)
        _print_active_no_source_report(active_no_source_rows)

    return 2 if (orphan_rows or active_no_source_rows) else 0


if __name__ == "__main__":
    sys.exit(main())
