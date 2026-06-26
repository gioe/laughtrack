-- Onboard The Public House at The Alexander (Colorado Springs, CO) — TASK-3439,
-- objective discover-comedy-venues near 80202.
--
-- The Public House at The Alexander is the historic-Alexander-building location
-- of the Public House pub & grill (thepublichouseco.com — a Wix site with no
-- events calendar of its own; only menu PDFs). Stand-up comedy at this address
-- is produced by "Pikes Punks Comedy Show", a monthly Colorado Springs comedy
-- showcase (russellkellercomedy.com/pikes-punks) that ticket-sells through its
-- own Eventbrite organizer feed (organizer id 35273577653, slug
-- pikes-punks-comedy-show — confirmed off live event detail pages). Every Pikes
-- Punks event lands at this one address.
--
-- Modeled as a roving-PRODUCER proxy + per-venue club (skill scrape-club Step 4):
--   * "Pikes Punks Comedy Show" — hidden producer proxy (visible=false) wired to
--     the generic `eventbrite` scraper in ORGANIZER mode (source_url contains
--     `/o/`). This drives the feed.
--   * "The Public House at The Alexander" — the fixed VENUE club (visible=true).
--     The Eventbrite events carry this venue name, so the scraper attributes the
--     producer's shows to this club by name. It needs NO scraping_source of its
--     own; the producer feed fills it.
--
-- The Eventbrite *venue* instance id (297677607) returns only a partial subset
-- (1 event) and drifts as Eventbrite reassigns venue-instance ids per event, so
-- it must NOT be used — the organizer id returns the full Pikes Punks calendar.
-- (A discovery-time mis-wire put venue id 297677607 directly on the venue club;
-- on a fresh DB that wiring does not exist, so this migration omits it.)
--
-- Verified: make scrape-club-id ID=<producer> => 1 show
-- ("Pikes Punks Comedy Show: Billy Anderson", 2026-06-27 8:00 PM MDT) attributed
-- to the visible venue club. Pikes Punks is monthly, so 1 upcoming show is the
-- expected steady-state count.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Producer proxy (hidden; drives the Eventbrite organizer feed).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Pikes Punks Comedy Show',
       '3104 N Nevada Ave, Colorado Springs, CO 80907, USA',
       'https://www.eventbrite.com/o/pikes-punks-comedy-show-35273577653',
       'Colorado Springs', 'CO', '80907', 'America/Denver', 'US', 'club',
       'ChIJKTnueNK9cYkRBolLyz3zyyU', false, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Pikes Punks Comedy Show');

-- 2. Fixed venue (visible; receives the producer's shows by venue-name match).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Public House at The Alexander',
       '3104 North Nevada Avenue, Colorado Springs, CO',
       'https://www.thepublichouseco.com/',
       'Colorado Springs', 'CO', '80907', 'America/Denver', 'US', 'club',
       'ChIJG7PCBX9PE4cRACwcIaz3jwY', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Public House at The Alexander');

-- 3. Eventbrite organizer-mode scraping source on the producer proxy. No unique
--    constraint beyond PK, so guard with NOT EXISTS on (club_id, scraper_key);
--    also guard the globally-unique eventbrite_id so a pre-existing row elsewhere
--    cannot trip the insert.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com/o/pikes-punks-comedy-show-35273577653', '35273577653', 0, true, '{}'
FROM clubs c
WHERE c.name = 'Pikes Punks Comedy Show'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  )
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss WHERE ss.eventbrite_id = '35273577653'
  );
