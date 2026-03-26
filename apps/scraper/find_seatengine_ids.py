"""
Enumerate SeatEngine venue IDs to build a name→id map,
then match against a list of club names to find correct IDs.

Usage:
  cd apps/scraper
  .venv/bin/python find_seatengine_ids.py
"""

import asyncio
import json
from pathlib import Path

from dotenv import dotenv_values
from curl_cffi.requests import AsyncSession

ENV_PATH = Path(__file__).parent / ".env"
SEATENGINE_BASE = "https://services.seatengine.com/api/v1"

# IDs to enumerate — covers range observed in the audit
ID_RANGES = list(range(1, 600))

# Clubs needing correct IDs
NEED_IDS = {
    62: "Sunken Bus Studios",
    63: "TK's",
    73: "The Comedy Zone Greenville",
    78: "Tommy T's Pleasanton",
    82: "Wicked Funny Comedy Club North Andover",
    85: "Arlington Drafthouse",
    89: "Beaches Comedy Club",
    91: "Bricktown Comedy Club Tulsa",
    100: "Comedy Off Broadway",  # confirmed correct is 449
    101: "Cozzys Comedy Club",
    103: "Denver Comedy Underground",
    105: "Elmwood Commons Theater",
    113: "Hilarities 4th Street Theatre",
    115: "Laughs Unlimited",  # confirmed correct is 472
    119: "Mic Drop Comedy Plano",
    120: "Mic Drop Mania",
    121: "Nate Jackson's Super Funny Comedy Club",  # confirmed correct is 478
    125: "Sticks and Stones Comedy Club",  # confirmed correct is 508
    131: "Summit City Comedy Club",
}

# Already-confirmed correct mappings from cross-reference analysis
CONFIRMED = {
    68: 432,   # Comedy Chateau → api shows 432 = The Comedy Chateau
    100: 449,  # Comedy Off Broadway → api shows 449 = Comedy Off Broadway
    115: 472,  # Laughs Unlimited → api shows 472 = Laughs Unlimited
    121: 478,  # Nate Jackson's → api shows 478 = Nate Jackson's
    125: 508,  # Sticks and Stones → api shows 508 = STICKS AND STONES COMEDY CLUB
}


async def enumerate_venues(session: AsyncSession, ids: list, token: str) -> dict:
    """Return {id: name} for all successfully fetched venue IDs."""
    results = {}
    headers = {"x-auth-token": token, "accept": "application/json"}
    semaphore = asyncio.Semaphore(10)  # 10 concurrent requests

    async def fetch_one(vid: int):
        async with semaphore:
            try:
                url = f"{SEATENGINE_BASE}/venues/{vid}"
                resp = await session.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    venue = data.get("data", data)
                    name = venue.get("name", "")
                    if name:
                        results[vid] = name.strip()
            except Exception:
                pass

    await asyncio.gather(*[fetch_one(vid) for vid in ids])
    return results


def normalize(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    v = dotenv_values(ENV_PATH)
    token = v["SEATENGINE_AUTH_TOKEN"]

    async def run():
        print(f"Enumerating {len(ID_RANGES)} SeatEngine venue IDs (this may take ~30s)...")
        async with AsyncSession(impersonate="chrome124") as session:
            id_to_name = await enumerate_venues(session, ID_RANGES, token)

        name_to_ids = {}
        for vid, name in id_to_name.items():
            key = normalize(name)
            name_to_ids.setdefault(key, []).append(vid)

        print(f"\nFound {len(id_to_name)} active venue IDs.\n")

        # Save for reference
        with open("/tmp/seatengine_id_map.json", "w") as f:
            json.dump({str(k): v for k, v in sorted(id_to_name.items())}, f, indent=2)
        print("Full map saved to /tmp/seatengine_id_map.json\n")

        print("=" * 80)
        print("SEARCH RESULTS FOR MISMATCHED CLUBS:")
        print("=" * 80)

        for club_id, club_name in sorted(NEED_IDS.items()):
            # Check confirmed first
            if club_id in CONFIRMED:
                confirmed_id = CONFIRMED[club_id]
                api_name = id_to_name.get(confirmed_id, "?")
                print(f"\n[{club_id}] {club_name}")
                print(f"  CONFIRMED: seatengine_id → {confirmed_id} (API: '{api_name}')")
                continue

            # Search by normalized name
            norm = normalize(club_name)
            matches = []
            for key, ids in name_to_ids.items():
                # Fuzzy: check if major tokens overlap
                club_tokens = set(norm.split()) if False else {norm[:8], norm[:12], norm}
                if any(t in key for t in [norm[:6]] if len(t) >= 4):
                    for vid in ids:
                        matches.append((vid, id_to_name[vid]))

            # Also try token-based search
            import re
            tokens = [t for t in re.split(r"[^a-z0-9]", normalize(club_name)) if len(t) >= 4]
            token_matches = []
            for key, ids in name_to_ids.items():
                if any(t in key for t in tokens):
                    for vid in ids:
                        api_name_full = id_to_name[vid]
                        token_matches.append((vid, api_name_full))

            # Deduplicate
            seen = set()
            all_matches = []
            for vid, name in token_matches:
                if vid not in seen:
                    seen.add(vid)
                    all_matches.append((vid, name))

            print(f"\n[{club_id}] {club_name}")
            if all_matches:
                for vid, name in sorted(all_matches):
                    print(f"  CANDIDATE: id={vid} → '{name}'")
            else:
                print(f"  NO MATCH FOUND — manual search needed")

    asyncio.run(run())


if __name__ == "__main__":
    main()
