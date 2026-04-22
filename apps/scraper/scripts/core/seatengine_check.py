"""
SeatEngine venue health check — single venue by ID.

Usage:
    cd apps/scraper && make seatengine-check ID=90

Exit codes:
  0 = healthy (venue exists, has shows)
  1 = error (missing args, missing token)
  2 = dead or empty
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from curl_cffi.requests import AsyncSession


API_BASE = "https://services.seatengine.com/api/v1"


async def check_venue(venue_id: str, auth_token: str) -> dict:
    """Check a single SeatEngine venue and return a status dict."""
    headers = {"x-auth-token": auth_token, "Accept": "application/json"}
    result = {"venue_id": venue_id, "venue_name": None, "show_count": 0, "status": "unknown", "reason": None}

    async with AsyncSession(impersonate="chrome124") as session:
        try:
            resp = await session.get(f"{API_BASE}/venues/{venue_id}", headers=headers, timeout=10)
            if resp.status_code == 404:
                result["status"] = "dead"
                result["reason"] = "venue API returned 404"
                return result
            elif resp.status_code == 200:
                venue = resp.json().get("data", resp.json())
                result["venue_name"] = venue.get("name")
            else:
                result["status"] = "error"
                result["reason"] = f"venue API returned HTTP {resp.status_code}"
                return result
        except Exception as e:
            result["status"] = "error"
            result["reason"] = str(e)
            return result

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


def lookup_club_by_seatengine_id(venue_id: str) -> dict | None:
    try:
        from laughtrack.adapters.db import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM clubs WHERE seatengine_id = %s", (venue_id,))
            row = cur.fetchone()
            cur.close()
            if row:
                return {"id": row[0], "name": row[1]}
    except Exception:
        pass
    return None


async def main():
    if len(sys.argv) < 2:
        print("Usage: make seatengine-check ID=<venue_id>")
        sys.exit(1)

    venue_id = sys.argv[1]
    auth_token = os.environ.get("SEATENGINE_AUTH_TOKEN", "")
    if not auth_token:
        print("ERROR: SEATENGINE_AUTH_TOKEN not set in .env")
        sys.exit(1)

    db_info = lookup_club_by_seatengine_id(venue_id)
    result = await check_venue(venue_id, auth_token)

    label = result["venue_name"] or (db_info["name"] if db_info else f"SE:{venue_id}")
    if db_info:
        label = f"{label} (club {db_info['id']})"

    if result["status"] == "healthy":
        print(f"✅ {label} — {result['show_count']} shows")
    else:
        print(f"❌ {label} — {result['reason']}")

    # JSON to stderr for machine consumption
    print(json.dumps(result), file=sys.stderr)
    sys.exit(0 if result["status"] == "healthy" else 2)


if __name__ == "__main__":
    asyncio.run(main())
