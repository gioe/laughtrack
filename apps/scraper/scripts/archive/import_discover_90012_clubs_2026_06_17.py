#!/usr/bin/env python3
"""
Import the discover-comedy-venues sweep of ZIP 90012 (100 mi radius, 2026-06-17)
into the web Postgres DB.

Sourced from scripts/core/discover_90012_2026_06_17.json (132 net-new candidates,
all classified "new" vs the clubs table). Each candidate was website-probed and
labelled high / medium / low. This script writes:

  * HIGH + MEDIUM (82) -> clubs rows, visible=FALSE (hidden until a scraping_sources
    row is wired per venue; avoids publishing empty pages and tripping the
    active-visible-needs-scraper invariant). ON CONFLICT (name) DO NOTHING.

  * LOW (50) -> venue_deny_list rows, keyed on google_place_id, so discover-nearby
    classifies them "denied" and never re-files an onboarding task.
    ON CONFLICT (google_place_id) DO NOTHING.

Idempotent: re-running inserts nothing already present. Reads DATABASE_URL from
apps/scraper/.env (same resolution as bin/query / bin/migrate).

Usage:
    cd apps/scraper && python scripts/core/import_discover_90012_clubs_2026_06_17.py [--commit]

Without --commit it runs a dry run (prints the planned writes, rolls back).
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
SCRAPER_ROOT = SCRIPT_DIR.parents[1]
DATA_FILE = SCRIPT_DIR / "discover_90012_2026_06_17.json"
ENV_FILE = SCRAPER_ROOT / ".env"

load_dotenv(ENV_FILE)
sys.path.insert(0, str(SCRAPER_ROOT / "src"))
from laughtrack.foundation.db_util import connect_with_retry  # noqa: E402

DENY_REASON = (
    "discover-comedy-venues 90012 (100mi) 2026-06-17 triage: not a comedy-first "
    "venue with its own scrapable calendar (comedy school, roving show hosted at "
    "another venue, individual/agency, or non-comedy venue)."
)

# Website-verified labels, keyed by Google place_id. Anything not listed here is
# treated as LOW (denylisted). 43 high + 39 medium = 82 club inserts.
HIGH = {
    "ChIJMRaHpyDHwoARfxdlrCdXjDQ",  # The Upstairs Comedy Club
    "ChIJOcdbL9vHwoARhLLmRCq2ki0",  # UCB (Sunset)
    "ChIJK5t5CDXHwoARYkpSBd-2ZsE",  # Lyric Hyperion Theater & Cafe
    "ChIJrbIP8sPBwoARnmn4fcUFWJU",  # The Clubhouse
    "ChIJEV0PuzO_woAR8t5H8l1Wyds",  # The Pack Theater
    "ChIJ24qcKKm5woAR4ueR1OHBOpY",  # Zebra Room Comedy
    "ChIJG94rmuCVwoARsqlScOt6bEo",  # Fourth Wall Comedy
    "ChIJxQflhz-5woARzD5VXPerrNM",  # The Hollywood Comedy
    "ChIJ-Xxey0a_woARdYN8KXhon1A",  # UCB Theatre (Franklin)
    "ChIJxVDHA_DBwoAR4wHzRF9LXv8",  # The Glendale Room
    "ChIJO2vwINW-woARqZPK4QsWOYA",  # The Groundlings Theatre & School
    "ChIJYQLAJGe_woARKwXbMB3AkLM",  # Best Comedy Club Near Me Theater
    "ChIJZ-DDsFzDwoARadcCIgKP1K0",  # The Ice House
    "ChIJCZ1sc824woARsQs2racTZu4",  # ComedySportz
    "ChIJ6ZPztieWwoAR5AjL_vPjEGo",  # LA Connection Comedy Theatre
    "ChIJG4khZNKVwoARa4E23Wug6jk",  # The Nitecap
    "ChIJFWFhOke6woARHLNAHNz53Uo",  # The FanaticSalon Theater
    "ChIJB3p0G2jbwoAR_3xyps4XW2Y",  # Astronaut City Comedy Club
    "ChIJwXV5QIm7woARztKdrUOJa44",  # The Crow
    "ChIJE8VdTKalwoARB60RjYY-GZE",  # Drunk Theatre Company (LA)
    "ChIJ82BI9I8z3YARpAv-0iYz0ac",  # Comedy Room
    "ChIJ8-2CZajZ3IARWBjna0FEFx4",  # Orange County Crazies
    "ChIJVVVVVd6GwoARhARM7YTFxz8",  # J.R.'s Comedy Club
    "ChIJq6qqqosg3YARELzn3T6Y2xk",  # Improv Collective
    "ChIJnxEQJTYn3YARBOiE65O9s70",  # Amazing Comedy Theater
    "ChIJJyvvp_nn3IARnfl_cLGdwtw",  # Irvine Improv
    "ChIJpSxQBgC53IARtY1XR30Z4-8",  # Improv Comedy Club (Dos Lagos / Corona)
    "ChIJG_zP_O-x3IARnwICOKUbCEI",  # The Hideaway Cafe & Lounge
    "ChIJrQ7jAZdVw4ARhp54lCqiGn4",  # Yaamava' Theater
    "ChIJtxZ_gkar3IARBoPSWRTIJTw",  # Improv School Redlands
    "ChIJVUtOzJNN6IARBRU84_KygZ0",  # JEST Improv
    "ChIJNzYLwyyt6YARnl5fuhFCKrU",  # New and Good Comedy
    "ChIJ9T9yL9et6YARyAMw-mx6cf4",  # The Bunker Theater
    "ChIJTfr0m5xlw4ARdqJdMBbsRlE",  # FunnyVille Comedy Club
    "ChIJN1vev1mt6YARQ03ODEEz_rQ",  # The Welcome Room
    "ChIJlXaTf_Gs6YARqsca8MH4Q-k",  # Ventura Improv Company
    "ChIJfZ_bUr9_24ARW76fOio3xbE",  # The Merc
    "ChIJUxxhdb-B24ARBVXwNqajSpI",  # Live at the Loft / Pechanga
    "ChIJzWYlvmBz3IAR1DsE6wMkC1o",  # Playgrounded
    "ChIJldr5OwAT6YARetS_s9rFFok",  # SB Comedy Club (Speakeasy)
    "ChIJaZna3ITz24ARoEhJywM-BmY",  # Grand Comedy Club & Pizzeria
    "ChIJCb5C3AkI3IARpv33OnWF7_Y",  # CCA ComedySportz
    "ChIJp2BV0xAb24AREVDImlDmMjQ",  # The Rock Gallery Comedy Club
}
MEDIUM = {
    "ChIJewhavEnGwoAR9ZSMQTUaxzI",  # The Lexington Bar
    "ChIJabdB69fHwoARYVLhd3IdVbM",  # The Stowaway
    "ChIJ41biDRXFwoARI0B0GGSFNd4",  # The Paramount
    "ChIJaTbuL07HwoARfhREBZw4qJk",  # The Virgil
    "ChIJR1uDmVnHwoARhul5xSB3FYE",  # The Stray Theater
    "ChIJ61Squi65woAR1T-9_xK_XaQ",  # Tao Comedy Studio
    "ChIJR-1x_rfBwoAR03r0LQWcIgs",  # WGIS
    "ChIJl4fXkM-_woARj4z0PJqdSjA",  # Yeah Mon Comedy Lounge
    "ChIJ8bH9NAK3woARrun4rOzSO4Y",  # Savoy Entertainment Center
    "ChIJOSevUgC_woARMKbvN8ssM-A",  # The Starlight Cabaret
    "ChIJrdkHZwm7woARDGKBGb5IYo4",  # Jam in the Van
    "ChIJ67c90Zy7woARlRswiCPw0ho",  # LA School of Comedy
    "ChIJeVtUf74Ipq4RVxp0azDXYHw",  # Rise Up Comedy
    "ChIJwTjGUNK-woARSOU17_-9urg",  # Flashback
    "ChIJ2WzoA8alwoARafJZhTEsKvA",  # Illusion Magic Lounge
    "ChIJWWXWjmgow4ARcTJXxz_xoUM",  # Chatterbox
    "ChIJB11Lsg0x3YARCGGDWYo4qds",  # Que Sera
    "ChIJ29uRvjsx3YARMJiiO10YxUg",  # Long Beach Terrace Theater
    "ChIJwbfJ7Nsp3YARzWA_5djcYQw",  # Doll Hut
    "ChIJEfIMdcIxw4AR4fJySx0mqZU",  # Claremont Packing House
    "ChIJU9wRozAl6IAR0aPliOq2MB4",  # Fred Kavli Theater
    "ChIJjQ4UtZg66IARCFFBt-t8cOI",  # Hillcrest Center for the Arts
    "ChIJpcMqGqA1w4ARf5hzmGspNl0",  # Hamburger Mary's - Ontario
    "ChIJX3QQ3RtKw4ARCCS06a5Mj6I",  # Lewis Family Playhouse
    "ChIJ1zhB0ZVbwoAR6BDmA2nZ3YI",  # The Showcase Venue
    "ChIJnw3EhJIl6IARKg25ukpGnQY",  # Free Range Comedy
    "ChIJ7zdNNzrp3IARwJHJQayr2U0",  # The Upper Room Presents
    "ChIJd3SM_fW16YARPMrL1KdPJnk",  # VENPROV / Ventura Improv
    "ChIJb3RPon9O6IARl4_PVvA6CzU",  # OPAC Oxnard
    "ChIJEx5sUflnw4ARap6RHI-_ST4",  # The New J Spot Comedy Club & Pool Hall
    "ChIJx3cGO_Os6YAR6uLYx9A52d0",  # Paddy's Bar & Lounge
    "ChIJY2eLNuJl24ARVtfRMWNvKP8",  # Derby's Bar & Grill
    "ChIJe7aGOjdu3IAR7jtXnOXsYGE",  # Oceanside Theatre Company
    "ChIJEfCWEeBv3IARuk8j9GUV7YY",  # The Jazzy Wishbone
    "ChIJ_4v6SAVy3IARpGwq-eeidtE",  # New Village Arts
    "ChIJdVUHCHgU6YARbN00D9--woU",  # The Red Piano
    "ChIJG2R4N40V6YARe34USxyZdjU",  # Night Lizard Brewing Company
    "ChIJi0oBC3gU6YARYKR4D4lH5_Q",  # SB Comedy Hideaway
    "ChIJD2VeFaQb24ARoU9ZSyUrfaY",  # The Club Downtown @ Hotel Zoso
}

# Already in the clubs table under a different name and/or a NULL google_place_id,
# so neither the ON CONFLICT(name) guard nor discover-nearby's place_id/fuzzy-name
# match caught them. Confirmed same-physical-address duplicates of show-bearing
# venues; excluded from the club insert (the 8 shells they created were deleted).
EXISTING_ELSEWHERE = {
    "ChIJaTbuL07HwoARfhREBZw4qJk",  # The Virgil            -> club 658 "The Setup LA"
    "ChIJZ-DDsFzDwoARadcCIgKP1K0",  # The Ice House         -> club 167 "Ice House Comedy Club" (390 shows)
    "ChIJ29uRvjsx3YARMJiiO10YxUg",  # Long Beach Terrace    -> club 4566 "Beverly O'Neill Center"
    "ChIJq6qqqosg3YARELzn3T6Y2xk",  # Improv Collective     -> club 794 "The Improv Collective" (168 shows)
    "ChIJU9wRozAl6IAR0aPliOq2MB4",  # Fred Kavli Theater    -> club 5405 "Fred Kavli Theatre (B of A PAC)"
    "ChIJX3QQ3RtKw4ARCCS06a5Mj6I",  # Lewis Family Playhouse-> club 5172 "Lewis Family Playhouse"
    "ChIJrQ7jAZdVw4ARhp54lCqiGn4",  # Yaamava' Theater      -> club 4691 "Yaamava Resort & Casino"
    "ChIJUxxhdb-B24ARBVXwNqajSpI",  # Live at the Loft      -> club 4560 "Pechanga Resort Casino" (44 shows)
}

ADDR_RE = re.compile(r"(?:^|,)\s*([^,]+?),\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?,?\s*USA?\s*$")


def parse_city_state_zip(address: str):
    m = ADDR_RE.search(address or "")
    if not m:
        return None, None, None
    return m.group(1).strip(), m.group(2), m.group(3)


def _partition(venues):
    """Split candidates into (club_inserts, denylist_inserts), dropping the
    EXISTING_ELSEWHERE place_ids that are already represented by another club."""
    clubs, denials = [], []
    for v in venues:
        pid = v["place_id"]
        if pid in EXISTING_ELSEWHERE:
            continue
        (clubs if pid in HIGH or pid in MEDIUM else denials).append(v)
    return clubs, denials


def _insert_clubs(cur, clubs):
    """Insert hidden club rows; returns (inserted_names, skipped_names)."""
    inserted, skipped = [], []
    for v in clubs:
        city, state, zipc = parse_city_state_zip(v["address"])
        cur.execute(
            """
            INSERT INTO clubs (name, address, website, google_place_id,
                               city, state, zip_code, visible)
            VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
            """,
            (v["name"], v["address"], v.get("website") or "",
             v["place_id"], city, state, zipc),
        )
        (inserted if cur.fetchone() else skipped).append(v["name"])
    return inserted, skipped


def _insert_denylist(cur, denials):
    """Insert venue_deny_list rows; returns the count actually inserted."""
    count = 0
    for v in denials:
        cur.execute(
            """
            INSERT INTO venue_deny_list (google_place_id, name, reason, added_by)
            VALUES (%s, %s, %s, 'discovery_triage')
            ON CONFLICT (google_place_id) DO NOTHING
            """,
            (v["place_id"], v["name"], DENY_REASON),
        )
        count += cur.rowcount
    return count


def main() -> None:
    commit = "--commit" in sys.argv[1:]
    venues = json.loads(DATA_FILE.read_text())
    clubs, denials = _partition(venues)

    print(f"Loaded {len(venues)} venues: {len(clubs)} club inserts "
          f"({sum(1 for v in clubs if v['place_id'] in HIGH)} high / "
          f"{sum(1 for v in clubs if v['place_id'] in MEDIUM)} medium), "
          f"{len(denials)} denylist.")
    print(f"Mode: {'COMMIT' if commit else 'DRY RUN (rollback)'}\n")

    conn = connect_with_retry(os.environ["DATABASE_URL"] if os.environ.get("DATABASE_URL")
                              else _compose_dsn())
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            inserted_clubs, skipped_clubs = _insert_clubs(cur, clubs)
            inserted_deny = _insert_denylist(cur, denials)
        conn.commit() if commit else conn.rollback()
    finally:
        conn.close()

    print(f"clubs inserted: {len(inserted_clubs)}")
    print(f"clubs skipped (already present): {len(skipped_clubs)}")
    for n in skipped_clubs:
        print(f"    - {n}")
    print(f"venue_deny_list inserted: {inserted_deny}")
    if not commit:
        print("\n(DRY RUN — nothing written. Re-run with --commit to apply.)")


def _compose_dsn() -> str:
    u, p = quote(os.environ["DATABASE_USER"], safe=""), quote(os.environ["DATABASE_PASSWORD"], safe="")
    return (f"postgresql://{u}:{p}@{os.environ['DATABASE_HOST']}:"
            f"{os.environ.get('DATABASE_PORT', '5432')}/{os.environ['DATABASE_NAME']}?sslmode=require")


if __name__ == "__main__":
    main()
