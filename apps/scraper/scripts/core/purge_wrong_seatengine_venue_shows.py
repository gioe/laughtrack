#!/usr/bin/env python3
"""
Purge SeatEngine show rows that were ingested under the WRONG venue id and
orphaned when each club's seatengine_id was later corrected.

Background
----------
TASK-3498. ~56 seatengine clubs were originally onboarded with the wrong
``scraping_sources.seatengine_id`` (systematically off by ~15), so the scraper
ingested a DIFFERENT venue's shows under them. The ids were later bulk-corrected
to the right venues, but the pre-correction shows -- which carry
``show_page_url = https://services.seatengine.com/api/v1/venues/<WRONG_id>/shows/<n>``
-- orphaned under each club and were never reaped (the TASK-2847 stale-future
reconciler's safety cap blocks deleting a large future set at once). They now
surface in the app as another venue's lineup, frequently ``$0`` / "Free" with a
generic ticket link (the 2026-06-26 ticket-url repair masked this).

Confirmed via the live SeatEngine API: e.g. The Comedy Chateau (club 68) has
source_id=432 (correct) but 222 orphan rows carry venue 417 = "The Comedy Zone -
Charlotte"; Mic Drop Chandler 493 vs 478="Nate Jackson's Super Funny"; Cozzys 490
vs 475="Loonees Comedy Corner"; Bricktown Tulsa 467 vs 452="Rosa's Lounge".

What this script does
---------------------
1. Finds every show whose ``show_page_url`` embeds a SeatEngine venue id that
   differs from the club's CURRENT ``scraping_sources.seatengine_id`` (the
   authoritative, corrected id). Clubs with a NULL seatengine_id are included
   (the API-url rows there are stale orphans from a since-removed source).
2. For each distinct embedded venue id, resolves the venue NAME from the live
   SeatEngine API and compares it (normalized) to the club's name. A row is
   deleted ONLY when the embedded venue resolves to a genuinely DIFFERENT venue
   than the club -- the per-target shape validation. If the API can't be
   reached for an id, or the embedded venue name matches the club (a same-venue
   id/format change, not contamination), every row for that (club, venue id) is
   SKIPPED and reported, never deleted.
3. Deletes the confirmed-contaminated show rows. tickets / lineup_items /
   tagged_shows / sent_notifications cascade (FK onDelete: Cascade);
   ticket_purchase_click_events.show_id is set NULL (onDelete: SetNull).

Idempotent: a second run finds no candidates. Defaults to a dry run (rolls
back); pass --apply to commit.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/purge_wrong_seatengine_venue_shows.py            # dry run
    make run-script SCRIPT=scripts/core/purge_wrong_seatengine_venue_shows.py ARGS='--apply'
    make run-script SCRIPT=scripts/core/purge_wrong_seatengine_venue_shows.py ARGS='--club 68'
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import requests
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

TASK_ID = 3498
RECOVERY_LOG_PATH = _root / "docs" / "audits" / "task-3498-purge-wrong-seatengine-venue-shows.json"
_VENUE_ID_RE = re.compile(r"services\.seatengine\.com/api/v1/venues/([0-9]+)/")
_SEATENGINE_API = "https://services.seatengine.com/api/v1/venues/{venue_id}"


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


# Generic words shared by many comedy venues — ignored when deciding whether two
# names refer to the same establishment, so abbreviation/word-order/qualifier
# variants of ONE venue (e.g. "Fort Lauderdale Improv" vs "Ft. Lauderdale
# Improv", "Charlotte Comedy Zone" vs "The Comedy Zone - Charlotte") are not
# mistaken for two different venues.
_GENERIC_NAME_TOKENS = {
    "the", "a", "an", "of", "and", "at", "on", "in", "for",
    "comedy", "club", "lounge", "theatre", "theater", "co", "llc", "inc",
}


def _significant_tokens(name: Optional[str]) -> set[str]:
    """Lowercase non-generic word tokens of a venue/club name.

    Apostrophes are stripped before tokenizing so possessive variants align
    ("Governor's" and "Governors'" both -> "governors", "McGuire's" and
    "McGuires" both -> "mcguires") and don't read as different venues.
    """
    if not name:
        return set()
    collapsed = name.casefold().replace("'", "").replace("’", "")
    tokens = re.findall(r"[a-z0-9]+", collapsed)
    return {t for t in tokens if t not in _GENERIC_NAME_TOKENS}


def _is_different_venue(embedded_name: Optional[str], *reference_names: Optional[str]) -> bool:
    """True only when the embedded venue shares NO significant token with any reference.

    Conservative by design: any significant-token overlap (a shared proper noun,
    city, or distinctive word) with the club name OR the club's authoritative
    source-venue name is treated as the SAME venue (a benign id/format change),
    so the row is kept. Deletion requires the embedded venue to be a clearly
    distinct establishment.
    """
    if not embedded_name:
        return False  # unverifiable -> never delete
    embedded = _significant_tokens(embedded_name)
    if not embedded:
        return False
    for ref in reference_names:
        if embedded & _significant_tokens(ref):
            return False
    return True


def _resolve_venue_name(venue_id: int, token: str, cache: dict[int, Optional[str]]) -> Optional[str]:
    """Resolve a SeatEngine venue id to its name via the live API (cached).

    Returns the venue name, or None when the lookup fails (caller treats None as
    'cannot verify' and skips deletion).
    """
    if venue_id in cache:
        return cache[venue_id]
    name: Optional[str] = None
    try:
        resp = requests.get(
            _SEATENGINE_API.format(venue_id=venue_id),
            headers={"x-auth-token": token, "accept": "application/json"},
            timeout=20,
        )
        if resp.status_code == 200:
            payload = resp.json()
            data = payload.get("data", payload) if isinstance(payload, dict) else {}
            name = data.get("name") if isinstance(data, dict) else None
    except Exception:
        name = None
    cache[venue_id] = name
    return name


def _candidate_groups(cur: RealDictCursor, club_id: Optional[int]) -> list[dict[str, Any]]:
    """One row per (club_id, embedded venue id) where the embedded id != source id."""
    params: list[Any] = []
    club_pred = ""
    if club_id is not None:
        club_pred = "AND s.club_id = %s"
        params.append(club_id)
    cur.execute(
        f"""
        SELECT
            s.club_id,
            c.name AS club_name,
            (substring(s.show_page_url from 'venues/([0-9]+)/'))::int AS url_venue_id,
            cs.seatengine_id AS source_id,
            COUNT(*) AS rows,
            COUNT(*) FILTER (WHERE s.date > NOW()) AS future_rows,
            array_agg(s.id) AS show_ids
        FROM shows s
        JOIN clubs c ON c.id = s.club_id
        LEFT JOIN scraping_sources cs
               ON cs.club_id = s.club_id AND cs.platform = 'seatengine'
        WHERE s.show_page_url LIKE '%%services.seatengine.com/api/v1/venues/%%'
          {club_pred}
        GROUP BY s.club_id, c.name, url_venue_id, cs.seatengine_id
        HAVING (substring(s.show_page_url from 'venues/([0-9]+)/'))::int
               IS DISTINCT FROM cs.seatengine_id
        ORDER BY rows DESC
        """,
        tuple(params),
    )
    return [dict(r) for r in cur.fetchall()]


def run(*, apply: bool, club_id: Optional[int], token: str) -> dict[str, Any]:
    name_cache: dict[int, Optional[str]] = {}
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            groups = _candidate_groups(cur, club_id)

            confirmed: list[dict[str, Any]] = []
            skipped: list[dict[str, Any]] = []
            delete_ids: list[int] = []

            for g in groups:
                url_venue_id = g["url_venue_id"]
                venue_name = _resolve_venue_name(url_venue_id, token, name_cache)
                # The club's authoritative current venue name (from its corrected
                # source_id), used alongside the club name as a same-venue guard.
                source_name = (
                    _resolve_venue_name(g["source_id"], token, name_cache)
                    if g["source_id"] is not None
                    else None
                )
                entry = {
                    "club_id": g["club_id"],
                    "club_name": g["club_name"],
                    "url_venue_id": url_venue_id,
                    "url_venue_name": venue_name,
                    "source_id": g["source_id"],
                    "source_venue_name": source_name,
                    "rows": g["rows"],
                    "future_rows": g["future_rows"],
                }
                # Delete ONLY when the embedded venue shares no significant token
                # with the club name OR its authoritative source-venue name.
                # Unverifiable (API down) or same-venue variant -> skip.
                if _is_different_venue(venue_name, g["club_name"], source_name):
                    confirmed.append(entry)
                    delete_ids.extend(int(i) for i in g["show_ids"])
                else:
                    entry["skip_reason"] = (
                        "embedded venue shares a significant token with the club / source venue (same-venue id change)"
                        if venue_name
                        else "could not resolve embedded venue via API"
                    )
                    skipped.append(entry)

            deleted_count = 0
            if delete_ids:
                cur.execute(
                    "DELETE FROM shows WHERE id = ANY(%s)",
                    (delete_ids,),
                )
                deleted_count = cur.rowcount

            payload = {
                "task": f"TASK-{TASK_ID}",
                "applied": apply,
                "club_scope": club_id,
                "generated_at": datetime.now(timezone.utc),
                "summary": {
                    "candidate_groups": len(groups),
                    "confirmed_groups": len(confirmed),
                    "skipped_groups": len(skipped),
                    "rows_deleted": deleted_count,
                    "confirmed_clubs": len({c["club_id"] for c in confirmed}),
                    "confirmed_future_rows": sum(c["future_rows"] for c in confirmed),
                },
                "confirmed": confirmed,
                "skipped": skipped,
            }

            if apply:
                _write_recovery_log(payload)
            else:
                conn.rollback()
            return payload


def _write_recovery_log(payload: dict[str, Any]) -> None:
    RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECOVERY_LOG_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Purge wrong-venue-id contaminated SeatEngine shows (TASK-3498)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the deletions. Without this flag the script runs as a dry run and rolls back.",
    )
    parser.add_argument(
        "--club",
        type=int,
        default=None,
        help="Limit to a single club_id (useful for verification).",
    )
    args = parser.parse_args()

    token = os.environ.get("SEATENGINE_AUTH_TOKEN", "").strip()
    if not token:
        print("ERROR: SEATENGINE_AUTH_TOKEN is not set; cannot verify venues.", file=sys.stderr)
        return 1

    payload = run(apply=args.apply, club_id=args.club, token=token)
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))
    if not args.apply:
        print("DRY RUN: no rows deleted and no recovery log written. Re-run with --apply to commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
