#!/usr/bin/env python3
"""
Repeatable check: shows.last_scraped_by values exist in scrapers.key.

Invariant
---------
Every distinct value of ``shows.last_scraped_by`` must appear in
``scrapers.key``. NULL is permitted (rows whose attribution is unknown,
typically pre-backfill or from ambiguous URL hosts that the
20260509120000_add_shows_last_scraped_by migration left for the next
nightly run to resolve).

Why it matters
--------------
``shows.last_scraped_by`` is a free-text column with no FK to ``scrapers``
(see TASK-2059, surfaced from /review-commits comment 2466 on TASK-2051).
A typo in a new scraper's ``BaseScraper.key``, or a renamed/retired
scraper, silently produces orphan attribution values that audits then have
to reconcile manually. This check catches that drift before it accumulates.

Usage
-----
    cd apps/scraper
    .venv/bin/python scripts/core/check_show_attribution.py [--json]

Exits 0 when no orphans remain, 2 when orphan attribution values are
found, and 1 for execution/query errors.
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


_ORPHAN_QUERY = """
    SELECT
        s.last_scraped_by AS scraper_key,
        COUNT(*) AS show_count
    FROM shows s
    WHERE s.last_scraped_by IS NOT NULL
      AND s.last_scraped_by NOT IN (SELECT key FROM scrapers)
    GROUP BY s.last_scraped_by
    ORDER BY show_count DESC, s.last_scraped_by
"""


def _fetch_orphan_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(_ORPHAN_QUERY)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    return rows


def _format_row(row: dict[str, Any]) -> str:
    return f"  scraper_key={row['scraper_key']!r} show_count={row['show_count']}"


def _print_human_report(rows: list[dict[str, Any]], *, stream=None) -> None:
    if stream is None:
        stream = sys.stdout
    if not rows:
        print(
            "OK: All shows.last_scraped_by values are present in scrapers.key.",
            file=stream,
        )
        return

    print(
        f"ERROR: {len(rows)} shows.last_scraped_by value(s) missing from scrapers.key:",
        file=stream,
    )
    print(file=stream)
    for row in rows:
        print(_format_row(row), file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find shows.last_scraped_by values that do not exist in scrapers.key. "
            "Exits 2 when orphans are found, 0 otherwise."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON document on stdout instead of the human-readable report.",
    )
    args = parser.parse_args(argv)

    try:
        rows = _fetch_orphan_rows()
    except Exception as exc:
        print(
            f"ERROR: failed to query show attribution orphans: {exc}",
            file=sys.stderr,
        )
        return 1

    if args.json:
        print(json.dumps({"orphans": rows}, default=str, indent=2))
        _print_human_report(rows, stream=sys.stderr)
    else:
        _print_human_report(rows)

    return 2 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
