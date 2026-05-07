#!/usr/bin/env python3
"""
Repeatable check: enabled scraping_sources rows that share (club_id, priority).

Background
----------
The DB carries ``UNIQUE(club_id, platform, priority)`` on ``scraping_sources``,
so two rows with the SAME platform cannot co-exist at the same priority. But
two rows with DIFFERENT platforms CAN co-exist at the same priority — and
when both are ``enabled=true`` the scraper has no deterministic primary /
fallback ordering for that club. TASK-1950 first observed the symptom on
priority=0 SeatEngine v1/v3 pairs; TASK-1953 audited the SeatEngine slice;
TASK-1967 generalises the check across every platform.

What this script does
---------------------
1. Loads an optional allowlist (see ``_INTENTIONAL_EXCEPTIONS`` below) so
   knowingly-parallel configurations can be excluded with a written rationale.
2. Runs one query against the live scraper DB that GROUPs ``scraping_sources``
   by ``(club_id, priority)`` over ``enabled = true`` rows and reports any
   group with more than one row.
3. For every flagged row, prints ``source_id``, ``club_id``, ``club_name``,
   ``visible``, ``priority``, ``platform``, ``scraper_key``, ``external_id``,
   ``source_url`` and ``metadata`` — enough context to disposition without
   another query.
4. Exits 0 when no unexcepted duplicates remain; exits 2 when one or more
   duplicate groups are found (CI / cron consumers can branch on the code).
   Errors (missing token, DB unreachable, unknown args) exit 1.

Usage
-----
    cd apps/scraper
    make check-scraping-priorities                       # human-readable
    make run-script SCRIPT=scripts/core/check_duplicate_scraping_priorities.py ARGS='--json'

Or directly::

    cd apps/scraper && .venv/bin/python scripts/core/check_duplicate_scraping_priorities.py [--json]

The ``--json`` flag emits a single JSON document on stdout (groups + rows)
suitable for piping into jq or a follow-up disposition script. Stderr always
carries the human-readable summary so ``--json`` output stays parseable.
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


# Intentional exceptions: (club_id, priority) tuples that are knowingly
# allowed to host multiple enabled scraping_sources rows. Add an entry only
# when the parallel configuration is the durable answer for that venue
# (e.g. two endpoints that genuinely return disjoint events). Each entry MUST
# carry a rationale referencing the task that approved the exception, so the
# guard is auditable. As of TASK-1967 the allowlist is empty — every observed
# duplicate today is unintentional drift caused by seatengine_national's
# nightly upsert into priority=0 (see audit doc for details).
_INTENTIONAL_EXCEPTIONS: dict[tuple[int, int], str] = {
    # Example shape (uncomment + fill in only for a venue whose two enabled
    # priority-0 sources genuinely return DISJOINT events, e.g. a club that
    # sells some shows through Eventbrite and others through a custom widget
    # with no overlap. SeatEngine v1/v3 pairs are NOT this case — TASK-1953
    # confirmed both endpoints return identical data, so the right
    # disposition is to disable one, not allowlist the pair.
    # (<club_id>, <priority>): "TASK-XXXX: rationale referencing the approving task.",
}


_DUPLICATE_QUERY = """
    WITH duplicate_groups AS (
        SELECT club_id, priority
        FROM scraping_sources
        WHERE enabled = true
        GROUP BY club_id, priority
        HAVING COUNT(*) > 1
    )
    SELECT
        ss.club_id,
        c.name AS club_name,
        c.visible,
        ss.priority,
        ss.id AS source_id,
        ss.platform::text AS platform,
        ss.scraper_key,
        COALESCE(
            ss.seatengine_id::text,
            ss.seatengine_v3_id,
            ss.eventbrite_id,
            ss.ticketmaster_id,
            ss.wix_event_id,
            ss.ovationtix_id,
            ss.squadup_id
        ) AS external_id,
        ss.source_url,
        ss.metadata
    FROM duplicate_groups dg
    JOIN scraping_sources ss
      ON ss.club_id = dg.club_id
     AND ss.priority = dg.priority
     AND ss.enabled = true
    JOIN clubs c ON c.id = ss.club_id
    ORDER BY ss.club_id, ss.priority, ss.platform::text, ss.id
"""


def _fetch_duplicate_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(_DUPLICATE_QUERY)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    return rows


def _group_rows(rows: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["club_id"], row["priority"])
        grouped.setdefault(key, []).append(row)
    return grouped


def _split_grouped(
    grouped: dict[tuple[int, int], list[dict[str, Any]]],
    exceptions: dict[tuple[int, int], str],
) -> tuple[
    dict[tuple[int, int], list[dict[str, Any]]],
    dict[tuple[int, int], list[dict[str, Any]]],
]:
    """Return (unexcepted, excepted) groups."""
    unexcepted: dict[tuple[int, int], list[dict[str, Any]]] = {}
    excepted: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for key, group_rows in grouped.items():
        if key in exceptions:
            excepted[key] = group_rows
        else:
            unexcepted[key] = group_rows
    return unexcepted, excepted


def _format_row(row: dict[str, Any]) -> str:
    return (
        f"    ss.id={row['source_id']:<5} "
        f"platform={row['platform']:<14} "
        f"scraper_key={row['scraper_key']:<22} "
        f"external_id={str(row['external_id'] or '-'):<14} "
        f"source_url={row['source_url'] or '-'}"
    )


def _print_human_report(
    unexcepted: dict[tuple[int, int], list[dict[str, Any]]],
    excepted: dict[tuple[int, int], list[dict[str, Any]]],
    exceptions: dict[tuple[int, int], str],
    *,
    stream=None,
) -> None:
    if stream is None:
        stream = sys.stdout
    if unexcepted:
        print(
            f"❌ {len(unexcepted)} duplicate (club_id, priority) group(s) found "
            f"with multiple enabled scraping_sources rows:",
            file=stream,
        )
        print(file=stream)
        for (club_id, priority), group_rows in sorted(unexcepted.items()):
            sample = group_rows[0]
            print(
                f"  club={club_id} ({sample['club_name']!r}, visible={sample['visible']}) "
                f"priority={priority} n={len(group_rows)}",
                file=stream,
            )
            for row in group_rows:
                print(_format_row(row), file=stream)
            print(file=stream)
    else:
        print(
            "✅ No unexcepted duplicate (club_id, priority) groups with enabled rows.",
            file=stream,
        )

    if excepted:
        print(
            f"ℹ️  {len(excepted)} duplicate group(s) excepted via _INTENTIONAL_EXCEPTIONS:",
            file=stream,
        )
        for (club_id, priority), group_rows in sorted(excepted.items()):
            rationale = exceptions[(club_id, priority)]
            sample = group_rows[0]
            print(
                f"  club={club_id} ({sample['club_name']!r}) priority={priority}: {rationale}",
                file=stream,
            )


def _build_json_payload(
    unexcepted: dict[tuple[int, int], list[dict[str, Any]]],
    excepted: dict[tuple[int, int], list[dict[str, Any]]],
    exceptions: dict[tuple[int, int], str],
) -> dict[str, Any]:
    return {
        "duplicate_groups": [
            {
                "club_id": club_id,
                "priority": priority,
                "rows": rows,
            }
            for (club_id, priority), rows in sorted(unexcepted.items())
        ],
        "excepted_groups": [
            {
                "club_id": club_id,
                "priority": priority,
                "rationale": exceptions[(club_id, priority)],
                "rows": rows,
            }
            for (club_id, priority), rows in sorted(excepted.items())
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find enabled scraping_sources rows that share (club_id, priority). "
            "Exits 2 when unexcepted duplicates are found, 0 otherwise."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON document on stdout instead of the human-readable report.",
    )
    args = parser.parse_args(argv)

    try:
        rows = _fetch_duplicate_rows()
    except Exception as exc:
        print(f"ERROR: failed to query scraping_sources: {exc}", file=sys.stderr)
        return 1

    grouped = _group_rows(rows)
    unexcepted, excepted = _split_grouped(grouped, _INTENTIONAL_EXCEPTIONS)

    if args.json:
        payload = _build_json_payload(unexcepted, excepted, _INTENTIONAL_EXCEPTIONS)
        print(json.dumps(payload, default=str, indent=2))
        # Always emit the human summary on stderr too so JSON callers still
        # see the headline figure when reviewing logs.
        _print_human_report(unexcepted, excepted, _INTENTIONAL_EXCEPTIONS, stream=sys.stderr)
    else:
        _print_human_report(unexcepted, excepted, _INTENTIONAL_EXCEPTIONS)

    return 2 if unexcepted else 0


if __name__ == "__main__":
    sys.exit(main())
