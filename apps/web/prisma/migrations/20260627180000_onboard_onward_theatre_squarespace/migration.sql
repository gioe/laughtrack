-- Onboard Onward Theatre (Atlanta, GA) — TASK-3370,
-- objective #12 discover-comedy-venues near Atlanta 30303.
--
-- Onward Theatre is an improv comedy school-plus-venue. Although it is
-- class-heavy (classes live on a separate /classes page), its own site
-- (onwardtheatre.org) publishes a public show calendar at /eventschedule — a
-- Squarespace Events collection (typeName 'events-stacked',
-- collectionId 60b332e83717d7540bb14f4d) of ticketed improv/comedy performances
-- (musical improv showcases, 'Placebo', 'Eulogy', 'Direct Depozit',
-- 'Waacklanta', 'The Biggest Cast Ever'). The class registrations are NOT in
-- this collection, so no comedy/exclude filter is needed.
--
-- Datasource: wired to the existing generic `squarespace` scraper in events
-- mode — no net-new scraper needed. source_url is the full GetItemsByMonth
-- endpoint including the collectionId; the scraper fetches the current month
-- and the next two months.
--
-- Fixed venue -> visible=true.
--
-- Verification: `make scrape-club-id ID=11468` scraped 9 shows (club 11468,
-- source 7036), each show_page_url on the venue's own /eventschedule page.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Onward Theatre',
       '711 Catherine St SW, Atlanta, GA 30310',
       'https://onwardtheatre.org',
       'Atlanta', 'GA', '30310',
       'America/New_York', 'US', 'club',
       'ChIJv-2aCLoD9YgRiUgjWaoNTFs',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Onward Theatre'
     OR google_place_id = 'ChIJv-2aCLoD9YgRiUgjWaoNTFs'
);

-- 2. The squarespace scraping source: the GetItemsByMonth events endpoint.
-- Locate the club by name OR google_place_id for idempotency parity.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'squarespace', 'squarespace',
       'https://onwardtheatre.org/api/open/GetItemsByMonth?collectionId=60b332e83717d7540bb14f4d',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Onward Theatre' OR c.google_place_id = 'ChIJv-2aCLoD9YgRiUgjWaoNTFs')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'squarespace'
  );
