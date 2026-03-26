"""
Find correct SeatEngine IDs for all seatengine_classic clubs.

Enumerates the full ID range (1–700), then attempts name-based matching
for each mismatched club.

Usage:
  cd apps/scraper
  <python> find_seatengine_classic_ids.py
"""

import asyncio
import json
import re
from pathlib import Path

from dotenv import dotenv_values
from curl_cffi.requests import AsyncSession

ENV_PATH = Path(__file__).parent / ".env"
SEATENGINE_BASE = "https://services.seatengine.com/api/v1"
CACHE_PATH = Path("/tmp/seatengine_id_map_full.json")

# All 50 seatengine_classic clubs (from audit output)
CLASSIC_CLUBS = {
    42:  ("McGuire's Comedy Club",                   443, "mcguirescomedyclub.com"),
    43:  ("Brokerage Comedy Club",                   442, "brokeragecomedy.com"),
    44:  ("Governors' Comedy Club",                  441, "governorscomedyclub.com"),
    45:  ("Stress Factory",                          310, "stressfactory.com"),
    46:  ("Stress Factory Bridgeport",               311, "stressfactory.com"),
    47:  ("Comedy In Harlem",                        466, "comedyinharlem.com"),
    53:  ("Dania Improv",                            420, "daniaimprov.com"),
    57:  ("The Comedy Zone Greensboro",              448, "comedyzone.com"),
    58:  ("The Comedy Zone - Charlotte",             402, "comedyzone.com"),
    59:  ("Comedy Zone Jacksonville",                453, "comedyzone.com"),
    60:  ("The Comedy Zone - Cherokee",              504, "comedyzone.com"),
    64:  ("Tacoma Comedy Club",                      157, "tacomacomedyclub.com"),
    65:  ("The Caravan",                             230, "thecaravan.com"),
    66:  ("The Comedy Attic",                        206, "thecomedyattic.com"),
    67:  ("The Comedy Catch",                        425, "thecomedycatch.com"),
    69:  ("The Comedy Club of Kansas City",          338, "thecomedyclubkc.com"),
    70:  ("The Comedy Fort",                         401, "thecomedyfort.com"),
    71:  ("The Comedy Loft of DC",                   298, "comedyloftdc.com"),
    72:  ("The Comedy Vault",                        389, "thecomedyvault.com"),
    74:  ("The Comic Strip",                         162, "comicstripcomedy.com"),
    75:  ("The Dojo of Comedy",                      392, "thedojoofcomedy.com"),
    77:  ("The Well Comedy Club",                    487, "thewellcomedyclub.com"),
    79:  ("Underground Comedy",                      368, "undergroundcomedy.com"),
    81:  ("Vermont Comedy Club",                     124, "vermontcomedyclub.com"),
    83:  ("Wit's End Comedy Lounge",                 519, "witsendcomedy.com"),
    87:  ("Bananas Comedy Club Renaissance Hotel",   282, "bananascomedyclub.com"),
    88:  ("Barrel Room Portland",                    324, "barrelroompdx.com"),
    90:  ("Bricktown Comedy Club",                   359, "bricktowncomedyclub.com"),
    92:  ("Bricky's Comedy Club",                    561, "brickys.com"),
    94:  ("Capitol Hill Comedy Bar",                 588, "capitolhillcomedybar.com"),
    95:  ("Coastal Creative",                        564, "coastalcreative.com"),
    97:  ("Comedy Cabin",                            484, "comedycabin.com"),
   102:  ("DC Improv",                               275, "dcimprov.com"),
   104:  ("Desert Ridge Improv",                     328, "desertridgeimprov.com"),
   106:  ("Emerald City Comedy Club",                588, "emeraldcitycomedy.com"),
   107:  ("Fort Wayne Comedy Club @ 469",            270, "fortwaynecomedyclub.com"),
   108:  ("Helium & Elements Restaurant -St. Louis", 132, "heliumcomedy.com"),
   114:  ("Laugh Camp Comedy Club",                  537, "laughcampcomedy.com"),
   116:  ("Loonees Comedy Corner",                   460, "loonees.com"),
   117:  ("Louisville Comedy Club",                  414, "louisvillecomedyclub.com"),
   118:  ("Magoobys Joke House",                     301, "magoobys.com"),
   122:  ("Off The Hook Comedy Club",                192, "offthehookcomedy.com"),
   123:  ("Planet Of The Tapes",                     419, "planetofthetapes.com"),
   124:  ("Rooster T. Feathers Comedy Club",         483, "roostertfeathers.com"),
   126:  ("Snappers Fort Myers",                     159, "snapperscomedy.com"),
   127:  ("Snappers Palm Harbor",                    587, "snapperscomedy.com"),
   128:  ("Spokane Comedy Club",                     151, "spokanecomedyclub.com"),
   129:  ("StandUpLive Phoenix",                     336, "standuplive.com"),
   130:  ("Stress Factory - Valley Forge",           601, "stressfactory.com"),
   134:  ("Helium Comedy Club - Atlanta",            530, "heliumcomedy.com"),
}


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def token_search(club_name: str, id_to_name: dict) -> list:
    """Return list of (id, api_name) pairs whose name shares tokens with club_name."""
    stopwords = {"the", "comedy", "club", "improv", "theater", "theatre", "and", "of", "at"}
    tokens = [t for t in re.split(r"[^a-z0-9]+", normalize(club_name)) if len(t) >= 4 and t not in stopwords]
    matches = {}
    for vid, api_name in id_to_name.items():
        norm_api = normalize(api_name)
        if any(t in norm_api for t in tokens):
            matches[vid] = api_name
    return sorted(matches.items())


async def enumerate_venues(session: AsyncSession, ids: list, token: str) -> dict:
    results = {}
    headers = {"x-auth-token": token, "accept": "application/json"}
    semaphore = asyncio.Semaphore(15)

    async def fetch_one(vid: int):
        async with semaphore:
            try:
                url = f"{SEATENGINE_BASE}/venues/{vid}"
                resp = await session.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    venue = data.get("data", data)
                    name = venue.get("name", "")
                    website = venue.get("website", "")
                    if name:
                        results[vid] = {"name": name.strip(), "website": (website or "").strip()}
            except Exception:
                pass

    await asyncio.gather(*[fetch_one(vid) for vid in ids])
    return results


async def run():
    v = dotenv_values(ENV_PATH)
    token = v["SEATENGINE_AUTH_TOKEN"]

    if CACHE_PATH.exists():
        print(f"Loading cached full map from {CACHE_PATH}...")
        full_map = json.loads(CACHE_PATH.read_text())
        id_to_info = {int(k): info for k, info in full_map.items()}
    else:
        print("Enumerating SeatEngine IDs 1–700 (may take ~45s)...")
        async with AsyncSession(impersonate="chrome124") as session:
            id_to_info = await enumerate_venues(session, list(range(1, 701)), token)
        CACHE_PATH.write_text(json.dumps({str(k): info for k, info in sorted(id_to_info.items())}, indent=2))
        print(f"Saved {len(id_to_info)} entries to {CACHE_PATH}\n")

    id_to_name = {vid: info["name"] for vid, info in id_to_info.items()}
    id_to_website = {vid: info.get("website", "") for vid, info in id_to_info.items()}

    print(f"Loaded {len(id_to_name)} active venue IDs (max={max(id_to_name)})\n")
    print("=" * 100)
    print(f"SEARCH RESULTS FOR {len(CLASSIC_CLUBS)} SEATENGINE_CLASSIC CLUBS")
    print("=" * 100)

    for club_id in sorted(CLASSIC_CLUBS):
        club_name, current_id, known_website = CLASSIC_CLUBS[club_id]
        matches = token_search(club_name, id_to_name)

        # Also search by known website domain
        domain_key = known_website.replace("www.", "").replace(".com", "").replace(".net", "")
        website_matches = {}
        for vid, ws in id_to_website.items():
            if ws and domain_key and domain_key in ws.lower():
                website_matches[vid] = id_to_name[vid]

        print(f"\n[{club_id}] {club_name}  (current_id={current_id})")
        shown = set()
        # Union of token matches and website matches (both are sets of (vid, name) tuples).
        # If a vid appears in both, set deduplication keeps one entry; the [WEBSITE MATCH]
        # tag is then applied based on website_matches membership.
        for vid, name in sorted(set(matches) | set(website_matches.items())):
            ws = id_to_website.get(vid, "")
            tag = " [WEBSITE MATCH]" if vid in website_matches else ""
            print(f"  CANDIDATE: id={vid} → '{name}'  website={ws!r}{tag}")
            shown.add(vid)
        if not shown:
            print(f"  NO MATCH FOUND — manual search needed")


if __name__ == "__main__":
    asyncio.run(run())
