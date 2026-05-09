#!/usr/bin/env python3
"""
Backfill: HTML-decode show names that landed in the database with raw
entity escapes (TASK-2096).

An audit on 2026-05-09 found 96 future shows whose `name` column contained
un-decoded HTML entities such as `&amp;`, `&#8211;`, and `&nbsp;`, mostly
from etix and json_ld scrapers. The Show.__post_init__ boundary now calls
html.unescape() before whitespace normalization, but rows already in the
database need a one-shot cleanup.

This script is idempotent — it only touches rows where html.unescape() of
the current name produces a different string. Already-decoded names pass
through `unescape` unchanged.

Usage:
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_html_entities_in_show_names.py
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_html_entities_in_show_names.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/backfill_html_entities_in_show_names.py ARGS='--all-dates'
"""

import argparse
import html
import re
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_connection


def _normalize(name: str) -> str:
    """Mirror Show.__post_init__: html.unescape then collapse whitespace.

    Kept inline (not importing Show) so the script does not need the full
    laughtrack entity import chain or its DB stubs.
    """
    decoded = html.unescape(name)
    return re.sub(r"\s+", " ", decoded.strip())


def _fetch_candidates(all_dates: bool) -> list[tuple[int, str]]:
    """Return (id, name) for shows whose name still contains an HTML entity.

    Filters on the literal substrings `&amp;` / `&#` / `&lt;` / `&gt;` /
    `&quot;` / `&nbsp;` so we don't need to scan every row.
    """
    date_clause = "" if all_dates else "date >= NOW() AND "
    sql = f"""
        SELECT id, name
        FROM shows
        WHERE {date_clause}(
            name ILIKE '%&amp;%'
            OR name ILIKE '%&#%'
            OR name ILIKE '%&lt;%'
            OR name ILIKE '%&gt;%'
            OR name ILIKE '%&quot;%'
            OR name ILIKE '%&nbsp;%'
        )
        ORDER BY id
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [(r[0], r[1]) for r in cur.fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to the database.",
    )
    parser.add_argument(
        "--all-dates",
        action="store_true",
        help="Scan all shows, not just future ones (default: future only).",
    )
    args = parser.parse_args()

    candidates = _fetch_candidates(args.all_dates)
    if not candidates:
        print("No rows with HTML entities found — nothing to do.")
        return 0

    updates: list[tuple[int, str, str]] = []
    for show_id, raw in candidates:
        decoded = _normalize(raw)
        if decoded != raw:
            updates.append((show_id, raw, decoded))

    print(f"Scanned {len(candidates)} candidate rows; {len(updates)} need rewriting.")
    for show_id, raw, decoded in updates[:10]:
        print(f"  [{show_id}] {raw!r} → {decoded!r}")
    if len(updates) > 10:
        print(f"  … and {len(updates) - 10} more.")

    if args.dry_run:
        print("Dry run — no writes performed.")
        return 0

    if not updates:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for show_id, _raw, decoded in updates:
                cur.execute(
                    "UPDATE shows SET name = %s WHERE id = %s",
                    (decoded, show_id),
                )
        conn.commit()

    print(f"Updated {len(updates)} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
