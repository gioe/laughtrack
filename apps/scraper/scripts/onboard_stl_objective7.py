"""One-off onboarding for objective 7 (St. Louis discovery, TASK-3292 follow-ups).

Wires 5 venues to existing scrapers and creates 8 venue identity rows with NO
scraping_sources (null scraper). Idempotent: clubs guarded by ON CONFLICT(name),
sources guarded by NOT EXISTS(club_id, scraper_key). Safe to re-run.
"""

import json

from laughtrack.adapters.db import create_connection

TZ = "America/Chicago"

# (name, address, website, city, state, zip, place_id, visible)
CLUBS = [
    # --- 5 wired venues (visible) ---
    ("The Improv Shop", "3960 Chouteau Ave, St. Louis, MO 63110", "http://www.theimprovshop.com/", "St. Louis", "MO", "63110", "ChIJ5Wr7oNW02IcRzk8Iwp7apRI", True),
    ("KJ's Bar and Grill", "5300 N Broadway, St. Louis, MO 63147", "", "St. Louis", "MO", "63147", "ChIJUeqx9JNM34cRWAw4h1IEEfk", True),
    ("Graffiti Loft", "1802 S 9th St, St. Louis, MO 63104", "http://www.graffitiloft.com/", "St. Louis", "MO", "63104", "ChIJ1eBIa6Sz2IcRDBfDtvFavqA", True),
    ("CBA Event Center", "2619 Washington Ave, St. Louis, MO 63103", "", "St. Louis", "MO", "63103", "ChIJ-65Dc3Wz2IcRajlvW2QkctY", True),
    ("HollyLou Entertainment", "155 S Florissant Rd, Ferguson, MO 63135", "http://hollylouent.rocks/", "Ferguson", "MO", "63135", "ChIJm5NoOuA334cRLWZhfKaQdPM", True),
    # --- 8 venue-identity rows, NO scraper (hidden until/unless onboarded) ---
    ("Twisted Improv", "314 S Clay Ave, Kirkwood, MO 63122", "http://www.ktg-onstage.org/", "Kirkwood", "MO", "63122", "ChIJYd-J-i3M2IcRVmj2aEMU89s", False),
    ("Anti-Barrr Comedy Joint", "141 S Main St, Waterloo, IL 62298", "", "Waterloo", "IL", "62298", "ChIJ8WPGnI-92IcRIW9T4T6wjFM", False),
    ("The Heavy Anchor", "5226 Gravois Ave, St. Louis, MO 63116", "http://theheavyanchor.com/", "St. Louis", "MO", "63116", "ChIJ4YNx1M-12IcR994iWMwHKWA", False),
    ("Purple Quarters", "4170 Manchester Ave, St. Louis, MO 63110", "https://www.purplequartersstl.com/", "St. Louis", "MO", "63110", "ChIJk7dzRFm12IcR-kPYLncgksc", False),
    ("Greenfinch Theater & Dive", "2525 S Jefferson Ave, St. Louis, MO 63104", "http://greenfinchstl.com/", "St. Louis", "MO", "63104", "ChIJgeXKaKCz2IcRs2vKzwSsTlU", False),
    ("Westport Playhouse", "635 W Port Plaza Dr, St. Louis, MO 63146", "https://thewestportplayhouse.com/", "St. Louis", "MO", "63146", "ChIJS-0xaHky34cRH4PKj0arEBg", False),
    ("Hot Java Bar", "4193 Manchester Ave, St. Louis, MO 63110", "http://hotjava.bar/", "St. Louis", "MO", "63110", "ChIJhT_Nq9612IcRwgwqWUHIWW4", False),
    ("HandleBar", "4127 Manchester Ave, St. Louis, MO 63110", "http://www.handlebarstl.com/", "St. Louis", "MO", "63110", "ChIJt4ms6-i02IcRePJV_wR2Ll4", False),
]

COMEDY_FILTER = ["comedy", "stand[ -]?up", "comedian"]

# club_name -> (platform, scraper_key, source_url, eventbrite_id, metadata)
SOURCES = {
    "The Improv Shop": ("tribe_events", "the_events_calendar", "https://theimprovshop.com/wp-json/tribe/events/v1/events", None, {}),
    "KJ's Bar and Grill": ("eventbrite", "eventbrite", "https://www.eventbrite.com/o/89203190763", "89203190763", {}),
    "Graffiti Loft": ("eventbrite", "eventbrite", "https://www.eventbrite.com/o/graffiti-loft-121148654563", "121148654563", {"include_title_patterns": COMEDY_FILTER + ["corduroy lounge", "hazy brunch"]}),
    "CBA Event Center": ("eventbrite", "eventbrite", "https://www.eventbrite.com/o/black-ceasar-9372140944", "9372140944", {"include_title_patterns": COMEDY_FILTER + ["comedy jam"]}),
    "HollyLou Entertainment": ("eventbrite", "eventbrite", "https://www.eventbrite.com/venues/143661759/events/", "143661759", {"include_title_patterns": COMEDY_FILTER + ["laughs?", "jokes"]}),
}

conn = create_connection(autocommit=True)
cur = conn.cursor()

name_to_id = {}
for name, address, website, city, state, zipc, place_id, visible in CLUBS:
    cur.execute(
        """
        INSERT INTO clubs (name, address, website, city, state, zip_code, timezone,
                           country, club_type, google_place_id, visible, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'US', 'club', %s, %s, 'active')
        ON CONFLICT (name) DO NOTHING
        RETURNING id
        """,
        (name, address, website, city, state, zipc, TZ, place_id, visible),
    )
    row = cur.fetchone()
    if row:
        cid = row[0]
        action = "INSERTED"
    else:
        cur.execute("SELECT id FROM clubs WHERE name = %s", (name,))
        cid = cur.fetchone()[0]
        action = "EXISTS"
    name_to_id[name] = cid
    print(f"club {action:9} id={cid:<6} visible={str(visible):5} {name}")

print("--- scraping_sources ---")
for name, (platform, key, url, eb_id, meta) in SOURCES.items():
    cid = name_to_id[name]
    cur.execute(
        "SELECT 1 FROM scraping_sources WHERE club_id=%s AND scraper_key=%s",
        (cid, key),
    )
    if cur.fetchone():
        print(f"source EXISTS    club={cid} {key} {name}")
        continue
    cur.execute(
        """
        INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url,
                                      eventbrite_id, priority, enabled, metadata)
        VALUES (%s, %s::"ScrapingPlatform", %s, %s, %s, 0, true, %s::jsonb)
        RETURNING id
        """,
        (cid, platform, key, url, eb_id, json.dumps(meta)),
    )
    sid = cur.fetchone()[0]
    print(f"source INSERTED  id={sid} club={cid} {platform}/{key} {name}")

cur.close()
conn.close()
print("done")
