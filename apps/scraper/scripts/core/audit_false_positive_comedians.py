"""
TASK-605: Audit DB for false-positive comedian records.

Surfaces comedian records created from placeholder names (e.g. "TBA", "Special Guest")
that slipped through lineup extraction before TASK-603 added the deny-list filter.

Run:
    cd apps/scraper && .venv/bin/python scripts/core/audit_false_positive_comedians.py

Output columns:
    comedian_name   — the stored name
    lineup_count    — number of lineup_items rows pointing to this comedian
    sample_show_ids — up to 5 show IDs where the comedian appears (for targeted re-scraping)

Placeholder detection criteria (OR):
  1. Name matches a known placeholder string (case-insensitive): TBA, TBD, To Be Announced,
     Special Guest, Surprise Guest, Surprise Act, Mystery Guest, Comedy Show, Various Artists,
     Headliner, Featured Comedian, Local Comedian, Guest Comedian, Open Mic, Host, MC,
     Emcee, Opener, Headliner TBD, Lineup TBA, More TBA, Plus More, And More, And Special Guests
  2. Name length < 4 characters (single-name tokens that are almost never real comedian names)

Usage after reviewing results:
    - Note which clubs have the most affected shows.
    - Once TASK-603 is deployed (false-positive filter live), queue those clubs for re-scraping
      so lineup_items are healed with real comedian records.
"""

import os
import sys
from dotenv import load_dotenv

# Load scraper .env (not repo root)
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from laughtrack.infrastructure.database.connection import get_connection  # noqa: E402


AUDIT_QUERY = """
WITH placeholder_comedians AS (
    SELECT
        c.uuid,
        c.name
    FROM comedians c
    WHERE
        -- Known placeholder strings (case-insensitive)
        lower(c.name) = ANY(ARRAY[
            'tba', 'tbd', 'to be announced', 'to be determined',
            'special guest', 'special guests',
            'surprise guest', 'surprise act', 'mystery guest',
            'comedy show', 'various artists',
            'headliner', 'featured comedian', 'local comedian',
            'guest comedian', 'guest',
            'open mic', 'host', 'mc', 'emcee',
            'opener', 'opener tbd',
            'headliner tbd', 'lineup tba',
            'more tba', 'plus more', 'and more', 'and special guests',
            'comedian tba', 'comedian tbd',
            'comics tba', 'comics tbd'
        ])
        OR
        -- Short names (< 4 chars) — almost never a real comedian name
        length(trim(c.name)) < 4
)
SELECT
    pc.name                                             AS comedian_name,
    COUNT(li.show_id)                                   AS lineup_count,
    array_agg(DISTINCT li.show_id ORDER BY li.show_id)
        FILTER (WHERE li.show_id IS NOT NULL)           AS all_show_ids,
    (
        SELECT array_agg(x ORDER BY x)
        FROM (
            SELECT DISTINCT li2.show_id AS x
            FROM lineup_items li2
            WHERE li2.comedian_id = pc.uuid
            LIMIT 5
        ) sub
    )                                                   AS sample_show_ids
FROM placeholder_comedians pc
LEFT JOIN lineup_items li ON li.comedian_id = pc.uuid
GROUP BY pc.uuid, pc.name
HAVING COUNT(li.show_id) > 0
ORDER BY lineup_count DESC, comedian_name;
"""

CLUB_IMPACT_QUERY = """
WITH placeholder_comedians AS (
    SELECT c.uuid
    FROM comedians c
    WHERE
        lower(c.name) = ANY(ARRAY[
            'tba', 'tbd', 'to be announced', 'to be determined',
            'special guest', 'special guests',
            'surprise guest', 'surprise act', 'mystery guest',
            'comedy show', 'various artists',
            'headliner', 'featured comedian', 'local comedian',
            'guest comedian', 'guest',
            'open mic', 'host', 'mc', 'emcee',
            'opener', 'opener tbd',
            'headliner tbd', 'lineup tba',
            'more tba', 'plus more', 'and more', 'and special guests',
            'comedian tba', 'comedian tbd',
            'comics tba', 'comics tbd'
        ])
        OR length(trim(c.name)) < 4
)
SELECT
    cl.name                         AS club_name,
    cl.id                           AS club_id,
    COUNT(DISTINCT s.id)            AS affected_shows,
    COUNT(li.comedian_id)           AS affected_lineup_items
FROM placeholder_comedians pc
JOIN lineup_items li ON li.comedian_id = pc.uuid
JOIN shows s ON s.id = li.show_id
JOIN clubs cl ON cl.id = s.club_id
GROUP BY cl.id, cl.name
ORDER BY affected_shows DESC, club_name;
"""


def run_audit() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # --- Per-comedian breakdown ---
            print("=" * 72)
            print("FALSE-POSITIVE COMEDIAN AUDIT")
            print("=" * 72)
            cur.execute(AUDIT_QUERY)
            rows = cur.fetchall()
            if not rows:
                print("No false-positive comedian records found.")
            else:
                total_comedians = len(rows)
                total_lineup_items = sum(r[1] for r in rows)
                print(f"Found {total_comedians} false-positive comedian(s) "
                      f"across {total_lineup_items} lineup_item(s).\n")
                print(f"{'Comedian Name':<35} {'Lineup Count':>12}  Sample Show IDs")
                print("-" * 72)
                for name, count, _all_ids, sample_ids in rows:
                    sample_str = ", ".join(str(s) for s in (sample_ids or []))
                    print(f"{name:<35} {count:>12}  {sample_str}")

            # --- Per-club impact ---
            print("\n" + "=" * 72)
            print("CLUB IMPACT (clubs with affected shows)")
            print("=" * 72)
            cur.execute(CLUB_IMPACT_QUERY)
            club_rows = cur.fetchall()
            if not club_rows:
                print("No clubs affected.")
            else:
                print(f"\n{'Club Name':<40} {'Club ID':>8}  "
                      f"{'Affected Shows':>14}  {'Lineup Items':>12}")
                print("-" * 80)
                for club_name, club_id, affected_shows, affected_items in club_rows:
                    print(f"{club_name:<40} {club_id:>8}  "
                          f"{affected_shows:>14}  {affected_items:>12}")
                print(f"\nTotal clubs affected: {len(club_rows)}")

            print("\n" + "=" * 72)
            print("NEXT STEPS")
            print("=" * 72)
            print("1. Review the above — confirm the names listed are indeed placeholders.")
            print("2. Note the club IDs with the most affected shows.")
            print("3. After TASK-603 is deployed, re-scrape the affected clubs so that")
            print("   lineup_items are healed (placeholders will be filtered on ingestion).")


if __name__ == "__main__":
    run_audit()
