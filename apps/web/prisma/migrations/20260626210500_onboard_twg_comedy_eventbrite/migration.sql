-- Onboard TWG Comedy (St. Paul, MN) — TASK-3324
-- (discover-comedy-venues near 55101; Google primary_type=comedy_club).
--
-- TWG Comedy is St. Paul's homegrown comedy night hosted at The Warrior's Garden
-- (a cannabis wellness shop, 282 6th St E): a weekly free open mic plus recurring
-- ticketed showcases (Giggle Drama, Gateway Show, Gen Z Comedy, guest headliners).
-- The venue's own site (twgcomedy.com -> warriorsgarden.org/twg-comedy.html) is a
-- static Weebly page with no structured calendar — but every show is published on
-- the venue's own Eventbrite organizer "TWG Comedy" (id 93850123173, 44 live events).
--
-- Datasource: the venue's own Eventbrite organizer, wired to the generic
-- `eventbrite` scraper in SINGLE-VENUE mode (convention #192): source_url omits the
-- /o/ segment and eventbrite_id holds the organizer id. All events are at one
-- physical venue whose Eventbrite venue name ("The Warrior's Garden - Hemp &
-- Wellness") differs from this club's name, so organizer mode would create a
-- duplicate per-venue auto-club and split shows (TASK-3151 caveat). Single-venue
-- mode forces every show onto this one club. The /venues/{id}/events/ probe for the
-- organizer id returns 404 (not 200+empty), so the venue->organizer fallback fires
-- and the scrape lands all events.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 44 shows onto the single club
-- (no duplicate auto-club created).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'TWG Comedy',
       '282 6th St E Ste 102, St Paul, MN 55101',
       'http://www.twgcomedy.com',
       'St Paul', 'MN', '55101', 'America/Chicago', 'US', 'club',
       'ChIJ02EfD4vV94cRmIFQaoD4m4k', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'TWG Comedy');

-- 2. Eventbrite single-venue source (no /o/ in source_url; eventbrite_id = organizer
--    id). Guard with NOT EXISTS on (club_id, scraper_key) — no unique constraint
--    beyond the PK.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite', 'https://www.eventbrite.com', '93850123173', 0, true,
       '{}'::jsonb
FROM clubs c
WHERE c.name = 'TWG Comedy'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  );
