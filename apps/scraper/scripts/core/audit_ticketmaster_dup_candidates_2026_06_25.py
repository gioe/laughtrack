#!/usr/bin/env python3
"""
Detect ticketmaster bulk-import duplicate club rows shadowing an established
non-ticketmaster venue (TASK-3459).

Why not a same-(city, state) join
---------------------------------
The national-chain ticketmaster import added ~900 venues. A naive
same-(city, state) join against existing clubs over-matches wildly — every
arena/theatre shares a city with some comedy club ("Akron Civic Theatre" vs
"KillBox Comedy Club"), producing ~140 bogus pairs. The real bulk-import
duplicate signature is a shared *distinctive brand token*, not a shared city
word: "Stress Factory Comedy Club - Bridgeport" vs "Stress Factory Bridgeport"
share {stress, factory}; "Funny Bone Comedy Club - Albany" vs "Albany Funny
Bone" share {funny, bone}.

What this detector does
-----------------------
For every ticketmaster-sourced visible club, it finds same-(city, state)
visible non-ticketmaster clubs and scores them by overlap of *distinctive*
tokens — name tokens with generic comedy words AND the venue's own city/state
words removed. A non-empty distinctive overlap means the two rows name the same
venue (different spelling), i.e. a fold candidate. City-only matches (different
venues in the same city) score 0 and drop out.

It is READ-ONLY: it prints ranked candidates for human review. Confirm each by
comparing street addresses before folding (see
scripts/core/fold_remaining_tm_chain_dups_2026_06_25.py). The brand token
"improv" is treated as generic, so Improv-chain multi-room rows
("X Improv (Main Room)") fall out as city-only — those are deliberate room
splits, not duplicates, and need separate judgement.

Usage
-----
    cd apps/scraper
    make run-script SCRIPT=scripts/core/audit_ticketmaster_dup_candidates_2026_06_25.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_transaction

# Generic words that are not distinctive brand signal. "improv" is here on
# purpose: it is both the Improv chain brand and a generic comedy word, and the
# Improv multi-room rows are deliberate splits we do not want to auto-flag.
GENERIC = {
    "the", "comedy", "club", "at", "of", "and", "a", "theatre", "theater",
    "live", "bar", "grill", "lounge", "cafe", "company", "co", "center",
    "centre", "presents", "show", "shows", "improv", "room", "main", "stage",
    "events", "event", "dinner", "restaurant", "pub", "tavern", "house",
    "hall", "lab", "casino", "hotel", "resort", "spa", "ballroom",
}

CANDIDATE_SQL = """
    SELECT
        tm.id AS tm_id, tm.name AS tm_name,
        (SELECT COUNT(*) FROM shows s WHERE s.club_id = tm.id) AS tm_shows,
        o.id AS o_id, o.name AS o_name,
        (SELECT COUNT(*) FROM shows s WHERE s.club_id = o.id) AS o_shows,
        lower(o.city) AS city, o.state AS state,
        (SELECT COALESCE(string_agg(DISTINCT s2.platform::text, '/'), '')
           FROM scraping_sources s2 WHERE s2.club_id = o.id) AS o_platforms
    FROM clubs tm
    JOIN clubs o
      ON lower(o.city) = lower(tm.city)
     AND lower(o.state) = lower(tm.state)
     AND o.id <> tm.id
     AND o.visible
     AND o.status IS DISTINCT FROM 'closed'
     AND NOT EXISTS (
         SELECT 1 FROM scraping_sources sx
         WHERE sx.club_id = o.id AND sx.platform = 'ticketmaster'
     )
    WHERE tm.visible
      AND tm.status IS DISTINCT FROM 'closed'
      AND EXISTS (
          SELECT 1 FROM scraping_sources st
          WHERE st.club_id = tm.id AND st.platform = 'ticketmaster'
      )
"""


def _tokens(name: str) -> list[str]:
    name = (name or "").lower().replace("&", " and ")
    return [t for t in re.sub(r"[^a-z0-9]+", " ", name).split() if len(t) > 2]


def _distinctive(name: str, city: str, state: str) -> set[str]:
    blocked = set(_tokens(city)) | {(state or "").lower()}
    return {t for t in _tokens(name) if t not in GENERIC and t not in blocked}


def main() -> int:
    with get_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(CANDIDATE_SQL)
            rows = [dict(r) for r in cur.fetchall()]

    candidates = []
    for r in rows:
        shared = _distinctive(r["tm_name"], r["city"], r["state"]) & _distinctive(
            r["o_name"], r["city"], r["state"]
        )
        if not shared:
            continue
        candidates.append((sorted(shared), r))
    candidates.sort(key=lambda x: (-len(x[0]), x[1]["state"]))

    print(f"ticketmaster dup candidates (shared distinctive brand token): {len(candidates)}")
    for shared, r in candidates:
        print(
            f"tm {r['tm_id']} {r['tm_name']!r} (sh{r['tm_shows']}) "
            f"<~ canon {r['o_id']} {r['o_name']!r} (sh{r['o_shows']}) "
            f"[{r['o_platforms']}] {r['state']} brand={shared}"
        )
    print(
        "\nReview each: confirm same venue by street address before folding. "
        "Casino/hotel ballrooms, '<X> City'/'City Winery', and Improv "
        "'(Main Room)'/'(The Lab)' rows are NOT duplicates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
