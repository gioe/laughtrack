-- Onboard License No. 1 (Boulder, CO) — TASK-3415, objective #13
-- (discover-comedy-venues near 80202).
--
-- License No. 1 is a speakeasy bar in the Hotel Boulderado. Its basement hosts
-- "The Underground Comedy Showcase," a recurring stand-up series (Wed/Thu/Fri 8pm,
-- Sat 7:30pm & 9:15pm) produced by ComicCents (comiccents.com). ComicCents sells
-- every show through a single Eventbrite organizer feed ("ComicCents.com Presents",
-- organizer id 55483251983) and produces EXCLUSIVELY at License No. 1, so the
-- venue is a fixed visible club (not a roving-producer proxy) wired to the generic
-- `eventbrite` scraper in ORGANIZER mode (source_url contains `/o/`).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'License No. 1',
       '2115 13th St, Boulder, CO 80302',
       'https://www.license1boulderado.com/',
       'Boulder', 'CO', '80302', 'America/Denver', 'US', 'club',
       'ChIJwa5bxyfsa4cR6C5L7eKShXw', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'License No. 1');

-- 2. Eventbrite organizer-mode scraping source (no unique constraint beyond PK,
--    so guard with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com/o/comiccentscom-presents-55483251983', '55483251983', 0, true, '{}'
FROM clubs c
WHERE c.name = 'License No. 1'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  );
