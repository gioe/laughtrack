"""
One-off audit: verify all SeatEngine Classic seatengine_id mappings against the API.

Usage:
  cd apps/scraper
  .venv/bin/python audit_seatengine_classic_ids.py [--fix-sql]

Prints a table comparing DB club name to SeatEngine API venue name.
Flags mismatches with *** MISMATCH ***.

With --fix-sql, also prints a SQL migration for all confirmed mismatches.
"""

import argparse
import asyncio
import os
import re
import sys

from curl_cffi.requests import AsyncSession

from laughtrack.infrastructure.database.connection import get_connection


SEATENGINE_BASE = "https://services.seatengine.com/api/v1"


def loose_match(db_name: str, api_name: str) -> bool:
    """Return True if names loosely match (case-insensitive, strip filler words)."""
    stopwords = {"the", "comedy", "club", "theater", "theatre", "improv", "-", "&", "and"}

    def normalize(s: str) -> set:
        tokens = re.split(r"[\s\-&]+", s.lower())
        return {t for t in tokens if t and t not in stopwords}

    db_tokens = normalize(db_name)
    api_tokens = normalize(api_name)
    if not db_tokens or not api_tokens:
        return False
    overlap = db_tokens & api_tokens
    # At least one non-trivial token must match
    return len(overlap) >= 1


async def fetch_venue(session: AsyncSession, venue_id: str, token: str) -> dict | None:
    url = f"{SEATENGINE_BASE}/venues/{venue_id}"
    headers = {"x-auth-token": token, "accept": "application/json"}
    try:
        resp = await session.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", data)
        return None
    except Exception:
        return None


async def run_audit(fix_sql: bool = False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, seatengine_id FROM clubs WHERE scraper = 'seatengine_classic' ORDER BY id"
            )
            clubs = cur.fetchall()

    token = os.environ["SEATENGINE_AUTH_TOKEN"]

    print(f"Auditing {len(clubs)} SeatEngine Classic clubs...\n")
    print(f"{'ClubID':>6}  {'DB Name':<40}  {'SE ID':>6}  {'API Venue Name':<40}  {'Status'}")
    print("-" * 110)

    mismatches = []

    async with AsyncSession(impersonate="chrome124") as session:
        for club_id, db_name, se_id in clubs:
            if not se_id:
                print(f"{club_id:>6}  {db_name:<40}  {'None':>6}  {'(no seatengine_id)':40}  SKIP")
                continue

            venue = await fetch_venue(session, se_id, token)
            if venue is None:
                print(f"{club_id:>6}  {db_name:<40}  {se_id:>6}  {'(API error/not found)':40}  ERROR")
                mismatches.append((club_id, db_name, se_id, None))
                continue

            api_name = venue.get("name", "")
            match = loose_match(db_name, api_name)
            status = "OK" if match else "*** MISMATCH ***"
            print(f"{club_id:>6}  {db_name:<40}  {se_id:>6}  {api_name:<40}  {status}")

            if not match:
                mismatches.append((club_id, db_name, se_id, api_name))

            # Small delay to avoid hammering the API
            await asyncio.sleep(0.1)

    print(f"\n{'='*110}")
    if mismatches:
        print(f"\n{len(mismatches)} MISMATCH(ES) FOUND:\n")
        for club_id, db_name, se_id, api_name in mismatches:
            print(f"  club id={club_id}  db_name='{db_name}'  seatengine_id={se_id}  api_name='{api_name}'")
    else:
        print("\nAll mappings look correct. No mismatches found.")

    if fix_sql and mismatches:
        print("\n-- CORRECTIVE SQL (fill in correct seatengine_id values before running):")
        for club_id, db_name, se_id, api_name in mismatches:
            print(f"-- Club id={club_id} '{db_name}': current seatengine_id={se_id}, API returned '{api_name}'")
            print(f"-- UPDATE clubs SET seatengine_id = '<CORRECT_ID>' WHERE id = {club_id};")

    return mismatches


def main():
    parser = argparse.ArgumentParser(description="Audit SeatEngine Classic ID mappings")
    parser.add_argument("--fix-sql", action="store_true", help="Print corrective SQL stubs")
    args = parser.parse_args()

    mismatches = asyncio.run(run_audit(fix_sql=args.fix_sql))
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
