#!/usr/bin/env python3
"""Read-only ingestion-coverage review, including aggregate-fed venues.

A missing enabled per-club source is informational, not proof of missing
scraping. Recent persisted aggregate/organizer provenance demonstrates indirect
coverage. Other recent writes demonstrate activity without proving its source.
Only stale/absent evidence at active visible clubs requests operator review
(exit 2); this does not establish that ingestion is broken. Query errors exit 1.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_root = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()
)
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv

load_dotenv(_root / ".env")
from laughtrack.adapters.db import get_connection

# These implementations explicitly route shows onto discovered physical venues.
# Eventbrite is dual-mode: only organizer provenance proves indirect coverage.
# eventbrite_national is retired and is deliberately not accepted as evidence.
AGGREGATE_SCRAPER_KEYS = frozenset(
    {
        "ticketmaster_national",
        "next_stop_comedy",
        "ticket_tailor",
        "pabst_theater_group",
        "comedian_websites",
    }
)
DEFAULT_COVERAGE_DAYS = 7


def _recent(value: Any, as_of: datetime, days: int) -> bool:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
    if not isinstance(value, datetime) or value.tzinfo is None:
        return False
    return as_of - timedelta(days=days) <= value <= as_of


def is_aggregate_covered(
    row: dict[str, Any], as_of: datetime, days: int = DEFAULT_COVERAGE_DAYS
) -> bool:
    """Recognize recent persisted provenance on a single show (never its date)."""
    return (
        row.get("last_scraped_by") in AGGREGATE_SCRAPER_KEYS
        or row.get("scraped_by_organizer_id") is not None
    ) and _recent(row.get("last_scraped_date"), as_of, days)


_AGGREGATE_SQL = ", ".join("'" + key + "'" for key in sorted(AGGREGATE_SCRAPER_KEYS))
_NO_DIRECT_SOURCE_QUERY = f"""
    SELECT c.id AS club_id, c.name AS club_name, c.visible, c.status,
        COUNT(s.id) FILTER (WHERE s.date > NOW()) AS future_show_count,
        MIN(s.date) FILTER (WHERE s.date > NOW()) AS first_future_show,
        MAX(s.date) FILTER (WHERE s.date > NOW()) AS last_future_show,
        MAX(s.last_scraped_date) FILTER (
            WHERE s.last_scraped_date <= NOW()) AS last_last_scraped_date,
        MAX(s.last_scraped_date) FILTER (
            WHERE s.last_scraped_date <= NOW() AND (
                s.last_scraped_by IN ({_AGGREGATE_SQL})
                OR s.scraped_by_organizer_id IS NOT NULL
            )) AS last_aggregate_scraped_date
    FROM clubs c
    LEFT JOIN shows s ON s.club_id = c.id
    WHERE NOT EXISTS (
        SELECT 1 FROM scraping_sources ss
        WHERE ss.club_id = c.id AND ss.enabled = TRUE
    )
    GROUP BY c.id, c.name, c.visible, c.status
"""
# Preserve these fetcher interfaces for callers while changing their meaning:
# these are raw populations lacking a direct source, not established orphans.
_ORPHAN_FUTURE_SHOWS_QUERY = _NO_DIRECT_SOURCE_QUERY + """
    HAVING COUNT(s.id) FILTER (WHERE s.date > NOW()) > 0
    ORDER BY future_show_count DESC, c.id
"""
_ACTIVE_NO_SOURCE_QUERY = _NO_DIRECT_SOURCE_QUERY + """
    HAVING c.status = 'active' AND c.visible = TRUE
       AND COUNT(s.id) FILTER (WHERE s.date > NOW()) = 0
    ORDER BY c.id
"""


def _fetch_rows(query: str) -> list[dict[str, Any]]:
    with get_connection(autocommit=False) as conn:
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '60s'")
            cur.execute(query)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def _fetch_orphan_future_show_rows() -> list[dict[str, Any]]:
    return _fetch_rows(_ORPHAN_FUTURE_SHOWS_QUERY)


def _fetch_active_no_source_rows() -> list[dict[str, Any]]:
    return _fetch_rows(_ACTIVE_NO_SOURCE_QUERY)


# No arbitrary URLs, provider metadata or credentials are exported.
_REPORT_FIELDS = (
    "club_id",
    "club_name",
    "visible",
    "status",
    "future_show_count",
    "first_future_show",
    "last_future_show",
    "last_last_scraped_date",
    "last_aggregate_scraped_date",
)


def build_report(
    rows: list[dict[str, Any]], as_of: datetime, days: int = DEFAULT_COVERAGE_DAYS
) -> dict[str, Any]:
    classified = []
    for row in rows:
        item = {key: row.get(key) for key in _REPORT_FIELDS}
        if _recent(row.get("last_aggregate_scraped_date"), as_of, days):
            state = "aggregate_covered"
        elif _recent(row.get("last_last_scraped_date"), as_of, days):
            state = "recently_written_unknown_source"
        else:
            state = "coverage_unverified"
        item["coverage_state"] = state
        classified.append(item)
    unresolved = [r for r in classified if r["coverage_state"] == "coverage_unverified"]
    review = [r for r in unresolved if r["visible"] is True and r["status"] == "active"]
    return {
        "as_of": as_of.isoformat(),
        "coverage_days": days,
        "no_direct_source_clubs": classified,
        "aggregate_covered_clubs": [
            r for r in classified if r["coverage_state"] == "aggregate_covered"
        ],
        "recently_written_unknown_source_clubs": [
            r
            for r in classified
            if r["coverage_state"] == "recently_written_unknown_source"
        ],
        "coverage_unverified_clubs": unresolved,
        "review_required_clubs": review,
        # Legacy names retained for consumers, now limited to unresolved evidence.
        "orphan_future_show_clubs": [
            r for r in unresolved if (r["future_show_count"] or 0) > 0
        ],
        "active_no_source_clubs": [r for r in review if not r["future_show_count"]],
    }


def _print_report(report: dict[str, Any], stream: Any) -> None:
    print(
        f"INFO: {len(report['no_direct_source_clubs'])} club(s) lack a direct enabled source; "
        f"{len(report['aggregate_covered_clubs'])} have recent aggregate coverage; "
        f"{len(report['recently_written_unknown_source_clubs'])} have other recent writes.",
        file=stream,
    )
    rows = report["review_required_clubs"]
    if rows:
        print(
            f"REVIEW: {len(rows)} active visible club(s) have unverified ingestion coverage; "
            "absence of recent evidence does not prove ingestion is missing.",
            file=stream,
        )
        for row in rows:
            print(
                f"  club={row['club_id']} ({row['club_name']!r}) "
                f"future_shows={row['future_show_count']}",
                file=stream,
            )
    else:
        print(
            "OK: No active visible clubs need ingestion-coverage review.", file=stream
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review missing direct sources using recent ingestion provenance."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON; human diagnostics go to stderr."
    )
    parser.add_argument("--coverage-days", type=int, default=DEFAULT_COVERAGE_DAYS)
    args = parser.parse_args(argv)
    if args.coverage_days < 1 or args.coverage_days > 365:
        parser.error("--coverage-days must be between 1 and 365")
    try:
        rows = _fetch_orphan_future_show_rows() + _fetch_active_no_source_rows()
        report = build_report(rows, datetime.now(timezone.utc), args.coverage_days)
    except Exception as exc:
        # Exception messages may contain connection URLs/passwords.
        print(
            f"ERROR: failed to query scraping source invariants ({type(exc).__name__})",
            file=sys.stderr,
        )
        return 1
    if args.json:
        print(json.dumps(report, default=str, indent=2))
    _print_report(report, sys.stderr if args.json else sys.stdout)
    return 2 if report["review_required_clubs"] else 0


if __name__ == "__main__":
    sys.exit(main())
