-- Onboard The Louisville Underground (Louisville, CO) — TASK-3410, objective #13
-- (discover-comedy-venues near 80202).
--
-- The Louisville Underground is a comedy speakeasy at 640 Main St
-- ("COMEDY | LIVE MUSIC | GAME SHOWS"). Its Wix site
-- (thelouisvilleunderground.com) lists shows on a /tickets page via the
-- "Ticket Spot" Wix app (client.geteventviewer.com), which syncs the venue's
-- own Eventbrite organizer feed. Every event card links to
-- eventbrite.com/e/<slug>-<id>, and those events belong to Eventbrite organizer
-- "The Louisville Underground" (id 33945441325 — slug the-louisville-underground,
-- confirmed off a live event detail page).
--
-- Wiring the club to the generic `eventbrite` scraper in ORGANIZER mode
-- (source_url contains `/o/`) yields the dated show instances (comedy nights,
-- comedy specials, improv, game-show nights). The organizer feed groups events
-- by venue and they all land at this one address, so this is a FIXED venue
-- (visible=true), not a roving-producer proxy.
--
-- NOTE: a discovery-time mis-wire pointed the *sibling* discovered club
-- "Improv Boulder" (TASK-3409, same 640 Main St address) at this organizer; the
-- organizer slug unambiguously belongs to The Louisville Underground. On a fresh
-- DB neither the duplicate club nor that wiring exists, so this migration just
-- inserts the canonical venue + its Eventbrite source.
--
-- The Eventbrite *venue* id (295736370) returns only a partial subset (1 event)
-- and must NOT be used; the organizer id returns the full calendar.
--
-- Verified: make scrape-club-id => 12 shows (no stale-show reconciliation
-- conflict).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Venue club (fixed venue, visible).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Louisville Underground',
       '640 Main St, Louisville, CO 80027, USA',
       'https://www.thelouisvilleunderground.com/',
       'Louisville', 'CO', '80027', 'America/Denver', 'US', 'club',
       'ChIJIbtB3jTza4cRn2feIkyrhao', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Louisville Underground');

-- 2. Eventbrite organizer-mode scraping source (no unique constraint beyond PK,
--    so guard with NOT EXISTS on (club_id, scraper_key); also guard the globally
--    unique eventbrite_id so a pre-existing row elsewhere can't trip the insert).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com/o/the-louisville-underground-33945441325', '33945441325', 0, true, '{}'
FROM clubs c
WHERE c.name = 'The Louisville Underground'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  )
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss WHERE ss.eventbrite_id = '33945441325'
  );
