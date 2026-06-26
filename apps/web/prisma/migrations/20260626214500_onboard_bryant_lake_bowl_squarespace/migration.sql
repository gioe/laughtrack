-- Onboard Bryant Lake Bowl & Theater (Minneapolis, MN) — TASK-3326
-- (discover-comedy-venues near 55401; Google primary_type=bowling_alley — false
-- positive; it's an 82-seat theater with shows nearly nightly).
--
-- MIXED-USE venue (~45% comedy): the /theater calendar interleaves stand-up/improv
-- (Uproar Comedy Open Mic, Improv Zodiac, What's Next? Improv, Good Camel, Mo
-- Collins, Gross Domestic Punchlines) with music, plays, burlesque, drag, film
-- nights, and policy "edutainment". The Squarespace events feed carries NO
-- category/tag metadata, and comedy titles often lack keywords while non-comedy
-- titles sometimes contain them — so a precision-first comedy allowlist is used
-- (TASK-3326 decision; matches the Cloverdale Performing Arts Center include-filter
-- precedent, TASK-3236). The allowlist captures the recurring/clearly-comedy shows
-- with zero pollution; one-off comedy without keywords (e.g. A Drinking Game MN,
-- Clown Rodeo, The Tire Fires, Theater of Public Policy) is intentionally not
-- covered — precision over recall, to keep music/burlesque/plays out of prod.
--
-- Datasource: the venue's own Squarespace Events collection
--   GET https://www.bryantlakebowl.com/api/open/GetItemsByMonth?collectionId=5e7637deb3c84a5a842f6707
-- wired to the generic `squarespace` scraper with an include_title_patterns comedy
-- allowlist in scraping_sources.metadata.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 17 shows, all comedy (6
-- distinct titles: Good Camel Live, Gross Domestic Punchlines, Improv Zodiac!, Mo
-- Collins is Wigging Out!, Uproar Comedy Open Mic, What's Next? Improv & Variety) —
-- no music/burlesque/plays leaked.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Bryant Lake Bowl & Theater',
       '810 W Lake St, Minneapolis, MN 55408',
       'https://www.bryantlakebowl.com',
       'Minneapolis', 'MN', '55408', 'America/Chicago', 'US', 'club',
       'ChIJqRmGeoYn9ocROJ_rUgwsy0o', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Bryant Lake Bowl & Theater');

-- 2. Generic squarespace scraping source with a comedy include-filter for this
--    mixed-use calendar. Guard with NOT EXISTS on (club_id, scraper_key) — no
--    unique constraint beyond the PK.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://www.bryantlakebowl.com/api/open/GetItemsByMonth?collectionId=5e7637deb3c84a5a842f6707', 0, true,
       '{"include_title_patterns": ["comedy", "stand[- ]?up", "improv", "sketch", "open mic", "uproar", "punchlines", "good camel", "mo collins"]}'::jsonb
FROM clubs c
WHERE c.name = 'Bryant Lake Bowl & Theater'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'squarespace'
  );
