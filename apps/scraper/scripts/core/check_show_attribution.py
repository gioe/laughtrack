#!/usr/bin/env python3
"""
Repeatable check: shows.last_scraped_by values are recognised.

Invariant
---------
Every distinct value of ``shows.last_scraped_by`` must appear in
``scraping_sources.scraper_key`` OR be in the explicit
``_INTENTIONAL_EXCEPTIONS`` allowlist below. NULL is permitted (rows whose
attribution is unknown, typically pre-backfill or from ambiguous URL hosts
that the 20260509120000_add_shows_last_scraped_by migration left for the
next nightly run to resolve).

Why scraping_sources, not scrapers
----------------------------------
The ``scrapers`` table (added in 20260504143000_add_scrapers_table) is
intentionally sparse — it holds only the runtime-config bit
(``use_residential_proxy``) for the 5-6 IP-WAF-blocked platforms identified
in TASK-1892. It is NOT a registry of every scraper key. ``scraping_sources``
IS effectively that registry: every active venue scrape source carries a
``scraper_key``, and every scraper that persists a Show flows through a
configured source.

The ``_INTENTIONAL_EXCEPTIONS`` allowlist exists for keys that legitimately
write ``shows.last_scraped_by`` but bypass ``scraping_sources``. Today the
only such case is ``tour_dates`` (the Bandsintown comedian-tour-date
scraper, keyed by comedian rather than club —
src/laughtrack/scrapers/implementations/api/tour_dates/scraper.py).

Why it matters
--------------
``shows.last_scraped_by`` is a free-text column with no FK to anything
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


# Scraper keys that write shows.last_scraped_by but bypass scraping_sources.
# Add a one-line rationale per entry so future maintainers know why each is
# allowlisted. Keep this list short — every entry weakens the check.
_INTENTIONAL_EXCEPTIONS: frozenset[str] = frozenset({
    # Bandsintown comedian tour-date scraper — keyed by comedian, not club,
    # so it never has a corresponding scraping_sources row.
    "tour_dates",
})


_ORPHAN_QUERY = """
    SELECT
        s.last_scraped_by AS scraper_key,
        COUNT(*) AS show_count
    FROM shows s
    WHERE s.last_scraped_by IS NOT NULL
      AND s.last_scraped_by NOT IN (
          SELECT scraper_key FROM scraping_sources
          WHERE scraper_key IS NOT NULL
      )
      AND s.last_scraped_by != ALL(%s)
    GROUP BY s.last_scraped_by
    ORDER BY show_count DESC, s.last_scraped_by
"""


def _fetch_orphan_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(_ORPHAN_QUERY, (list(_INTENTIONAL_EXCEPTIONS),))
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
            "OK: All shows.last_scraped_by values are recognised "
            "(present in scraping_sources.scraper_key or allowlisted).",
            file=stream,
        )
        return

    print(
        f"ERROR: {len(rows)} unrecognised shows.last_scraped_by value(s) found "
        "(not in scraping_sources.scraper_key, not allowlisted):",
        file=stream,
    )
    print(file=stream)
    for row in rows:
        print(_format_row(row), file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find shows.last_scraped_by values that don't appear in "
            "scraping_sources.scraper_key (or the explicit allowlist). "
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
        traceback.print_exc(file=sys.stderr)
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
