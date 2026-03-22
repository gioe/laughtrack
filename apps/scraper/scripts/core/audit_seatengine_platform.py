"""
TASK-547: Audit all seatengine-scraped venues for classic vs. new platform.

Run: cd apps/scraper && .venv/bin/python scripts/core/audit_seatengine_platform.py

Background
----------
The SeatEngine platform has two versions:
- New (cdn-new.seatengine.com): exposes a REST API at services.seatengine.com/api/v1
- Classic (cdn.seatengine.com): server-rendered HTML, REST API returns {"data": []}

Clubs using the classic platform must use scraper='seatengine_classic'.
Clubs using the new platform use scraper='seatengine' (REST API).

Results from 2026-03-22 audit
------------------------------
Total audited:        77
Working (new API):    30  → keep scraper='seatengine'
Empty API response:   47  → all confirmed classic CDN → updated to seatengine_classic

The 47 migrated clubs included 5 with incorrect scraping_url values:
  [71]  The Comedy Loft of DC       dccomedyloft.com/events       → www.dccomedyloft.com/events
  [81]  Vermont Comedy Club          vtcomedy.com/events           → www-vermontcomedyclub-com.seatengine.com/calendar
  [102] DC Improv                    dcimprov.com/events           → dcimprov-com.seatengine.com/calendar
  [107] Fort Wayne Comedy Club       fortwaynecomedyclub.com/events → www.fortwaynecomedyclub.com/events
  [117] Louisville Comedy Club       louisvillecomedyclub.com/events → www.louisvillecomedy.com/events

Post-migration verification (spot checks)
------------------------------------------
  McGuire's Comedy Club (42):      0 → 30 shows  ✅
  DC Improv (102):                 0 → 135 shows ✅
  Tacoma Comedy Club (64):         0 → 163 shows ✅
  The Comedy Loft of DC (71):      0 → 135 shows ✅
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import requests
from curl_cffi.requests import AsyncSession
from laughtrack.adapters.db import get_connection


def get_clubs_by_scraper(scraper_type: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, scraper, scraping_url, seatengine_id FROM clubs WHERE scraper=%s ORDER BY id",
            (scraper_type,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows


def check_scraping_url_cdn(scraping_url: str) -> str:
    """Fetch the scraping_url and detect which SeatEngine CDN it loads."""
    if not scraping_url.startswith("http"):
        url = "https://" + scraping_url
    else:
        url = scraping_url
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True)
        content = resp.text
        if "cdn-new.seatengine.com" in content:
            return "new"
        elif "cdn.seatengine.com" in content:
            return "classic"
        return f"unknown (status={resp.status_code})"
    except Exception as e:
        return f"error: {type(e).__name__}"


async def check_all_venues_api(clubs, auth_token: str):
    """Hit services.seatengine.com REST API for each club and return results."""
    api_headers = {"x-auth-token": auth_token, "Accept": "application/json"}
    results = {}
    async with AsyncSession(impersonate="chrome124") as session:
        tasks = [
            (club, session.get(
                f"https://services.seatengine.com/api/v1/venues/{club[4]}/shows",
                headers=api_headers,
                timeout=10,
            ))
            for club in clubs
        ]
        for club, coro in tasks:
            try:
                resp = await coro
                if resp.status_code == 200:
                    data = resp.json()
                    shows = data.get("data", data.get("shows", []))
                    results[club[0]] = {"status": resp.status_code, "count": len(shows), "empty": len(shows) == 0}
                else:
                    results[club[0]] = {"status": resp.status_code, "count": 0, "empty": True}
            except Exception as e:
                results[club[0]] = {"status": "error", "count": 0, "empty": True, "error": str(e)}
    return results


async def main():
    auth_token = os.environ.get("SEATENGINE_AUTH_TOKEN", "")
    if not auth_token:
        print("ERROR: SEATENGINE_AUTH_TOKEN not set in .env")
        sys.exit(1)

    clubs = get_clubs_by_scraper("seatengine")
    print(f"Auditing {len(clubs)} clubs with scraper='seatengine'...")

    api_results = await check_all_venues_api(clubs, auth_token)
    empty = [(c, api_results[c[0]]) for c in clubs if api_results[c[0]]["empty"]]
    working = [(c, api_results[c[0]]) for c in clubs if not api_results[c[0]]["empty"]]

    print(f"\n✅ Working on new API: {len(working)}")
    for club, r in working:
        print(f"  [{club[0]:3}] {club[1]!r:50} → {r['count']} shows")

    print(f"\n❌ Empty on new API: {len(empty)} — checking CDN type...")
    classic_candidates = []
    for club, api_result in empty:
        cdn = check_scraping_url_cdn(club[3])
        tag = "→ NEEDS MIGRATION" if cdn == "classic" else ""
        print(f"  [{club[0]:3}] {club[1]!r:50} status={api_result['status']} CDN={cdn} {tag}")
        if cdn == "classic":
            classic_candidates.append(club)

    print(f"\nSUMMARY: {len(working)} new-API, {len(empty)} empty ({len(classic_candidates)} classic CDN)")
    if classic_candidates:
        print("\nRun the following to migrate:")
        ids = [c[0] for c in classic_candidates]
        print(f"  UPDATE clubs SET scraper='seatengine_classic' WHERE id IN ({','.join(map(str, ids))});")


if __name__ == "__main__":
    asyncio.run(main())
