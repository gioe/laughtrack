-- Onboard HammerJokes Comedy Club (Parkville, MD) — TASK-3334
-- (discover-comedy-venues near 21201; Google primary_type=comedy_club).
--
-- Active comedy club (operator Mickey Cucchiella) in the Bowman Restaurant
-- basement at 9306 Harford Rd: recurring Thu/Sat stand-up shows + Thu open mic,
-- named headliner lineups. Venue lineage at this address: Magooby's -> Sully's
-- Comedy Cellar -> HammerJokes (current). The superseded predecessor "Sully's
-- Comedy Cellar" (place_id ChIJ8dWF_dwIyIkRWQSh-Cn9JPk) is intentionally NOT
-- onboarded. (The separate, still-operating "Magooby's Joke House" in Timonium,
-- club 118, is a different active venue — not this address's predecessor.)
--
-- Datasource: the venue's own ThunderTix storefront
--   https://hammerjokes.thundertix.com
-- wired to the generic `thundertix` scraper (reads the venue base URL from
-- scraping_sources.source_url). Pure-comedy storefront, so no title filter needed.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 9 shows (named comedian
-- headliners; no class/non-comedy rows).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'HammerJokes Comedy Club',
       '9306 Harford Rd, Parkville, MD 21234',
       'https://www.hammerjokescomedy.com',
       'Parkville', 'MD', '21234', 'America/New_York', 'US', 'club',
       'ChIJHfC037IJyIkRLFj8b758aKE', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'HammerJokes Comedy Club');

-- 2. Generic thundertix scraping source (no unique constraint beyond PK, so guard
--    with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'thundertix', 'thundertix',
       'https://hammerjokes.thundertix.com', 0, true,
       '{}'::jsonb
FROM clubs c
WHERE c.name = 'HammerJokes Comedy Club'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'thundertix'
  );
