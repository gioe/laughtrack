"""
SeatEngine bulk health audit — check all seatengine-scraped clubs.

Usage:
    cd apps/scraper && make seatengine-audit

Exit codes:
  0 = all venues healthy
  1 = error (missing token, DB error)
  2 = at least one venue is dead or empty
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from curl_cffi.requests import AsyncSession
from laughtrack.adapters.db import get_connection


API_BASE = "https://services.seatengine.com/api/v1"


def get_seatengine_clubs() -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, seatengine_id FROM clubs "
            "WHERE scraper = 'seatengine' AND visible = true ORDER BY id"
        )
        cols = ["id", "name", "seatengine_id"]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        return rows


async def check_venue(session: AsyncSession, venue_id: str, headers: dict) -> dict:
    result = {"venue_id": venue_id, "show_count": 0, "status": "unknown", "reason": None}

    try:
        resp = await session.get(f"{API_BASE}/venues/{venue_id}", headers=headers, timeout=10)
        if resp.status_code == 404:
            return {**result, "status": "dead", "reason": "venue API returned 404"}
        elif resp.status_code != 200:
            return {**result, "status": "error", "reason": f"venue API returned HTTP {resp.status_code}"}
    except Exception as e:
        return {**result, "status": "error", "reason": str(e)}

    try:
        resp = await session.get(f"{API_BASE}/venues/{venue_id}/shows", headers=headers, timeout=10)
        if resp.status_code == 200:
            shows = resp.json().get("data", resp.json().get("shows", []))
            result["show_count"] = len(shows)
            result["status"] = "healthy" if shows else "empty"
            if not shows:
                result["reason"] = "0 upcoming shows"
        else:
            result["status"] = "empty"
            result["reason"] = f"shows API returned HTTP {resp.status_code}"
    except Exception as e:
        result["status"] = "error"
        result["reason"] = str(e)

    return result


async def audit_all(clubs: list[dict], auth_token: str) -> list[dict]:
    headers = {"x-auth-token": auth_token, "Accept": "application/json"}
    results = []

    async with AsyncSession(impersonate="chrome124") as session:
        tasks = []
        for club in clubs:
            se_id = club["seatengine_id"]
            if not se_id:
                results.append({**club, "show_count": 0, "status": "error", "reason": "no seatengine_id"})
                continue
            tasks.append((club, check_venue(session, str(se_id), headers)))

        for club, coro in tasks:
            try:
                api_result = await coro
                results.append({**club, **api_result})
            except Exception as e:
                results.append({**club, "show_count": 0, "status": "error", "reason": str(e)})

    return results


async def main():
    auth_token = os.environ.get("SEATENGINE_AUTH_TOKEN", "")
    if not auth_token:
        print("ERROR: SEATENGINE_AUTH_TOKEN not set in .env")
        sys.exit(1)

    clubs = get_seatengine_clubs()
    if not clubs:
        print("✅ No visible seatengine clubs found.")
        sys.exit(0)

    results = await audit_all(clubs, auth_token)
    failures = [r for r in results if r["status"] != "healthy"]

    if not failures:
        print(f"✅ All {len(results)} venues healthy")
    else:
        print(f"❌ {len(failures)} failed")
        for r in sorted(failures, key=lambda x: x["id"]):
            reason = r["reason"] if r["reason"] != "0 upcoming shows" else ""
            if reason:
                print(f"   {r['id']:>4}  {r['name']:<45} {reason}")
            else:
                print(f"   {r['id']:>4}  {r['name']}")

    # JSON to stderr for machine consumption
    print(json.dumps(results, default=str), file=sys.stderr)
    sys.exit(0 if not failures else 2)


if __name__ == "__main__":
    asyncio.run(main())
