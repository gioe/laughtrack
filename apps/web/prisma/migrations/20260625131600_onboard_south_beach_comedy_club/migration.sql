-- Onboard South Beach Comedy Club (Miami, FL) — TASK-3348, objective #11
-- (discover-comedy-venues near 33130/33301).
--
-- South Beach Comedy Club is a roving pop-up producer (Eventbrite organizer
-- id 87690878163, curated by @leetahfaye) whose "Comedy Night at ..." shows run
-- at varying Brickell-area venues (DOM'S, Aficionados Liquor Store & Mixology
-- Bar, ...). It is wired to the generic `eventbrite` scraper in ORGANIZER mode
-- (source_url contains `/o/`), which groups events by venue and upserts a
-- per-venue club for each, so the synthetic organizer club is hidden
-- (visible=false) and shows surface under the real per-venue clubs.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Synthetic (hidden) organizer club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'South Beach Comedy Club',
       '1010 Brickell Ave, Miami, FL 33131, USA',
       'https://www.eventbrite.com/o/87690878163',
       'Miami', 'FL', '33131', 'America/New_York', 'US', 'club',
       'ChIJHbre0ku32YgRg0vjAnrzxNI', false, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'South Beach Comedy Club');

-- 2. Eventbrite organizer-mode scraping source (no unique constraint beyond PK,
--    so guard with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com/o/87690878163', '87690878163', 0, true, '{}'
FROM clubs c
WHERE c.name = 'South Beach Comedy Club'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  );
