-- Onboard Gold Coast Comedy (Fort Lauderdale, FL) — TASK-3352,
-- objective #11 discover-comedy-venues near Miami 33130 / Fort Lauderdale 33301.
--
-- Gold Coast Comedy is a roving comedy PRODUCER, not a fixed venue: it runs
-- recurring weekly comedy at multiple bars/restaurants via its own Eventbrite
-- organizer "Gold Coast Comedy" (id 26218736367) — e.g. Ovivi's Speakeasy Comedy
-- Show and Bokampers Comedy Night.
--
-- Datasource: the producer's Eventbrite organizer, wired to the generic
-- `eventbrite` scraper in ORGANIZER mode (convention #251): source_url CONTAINS
-- the /o/ segment, which the scraper auto-detects to enable per-event venue
-- routing — it auto-creates a visible per-venue club for each physical venue
-- (Bokampers Sports Bar & Grill, Ovivi's Restaurant) and assigns each show there.
-- The producer itself is therefore a HIDDEN PROXY (visible=false): its own
-- total_shows stays 0 and the shows surface under the auto-created venue clubs,
-- exactly the convention #251 rule (hidden proxy only when the scraper routes
-- per-venue; otherwise visible=true single-venue mode).
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 60 shows, routed to two
-- auto-created visible venue clubs — Bokampers Sports Bar & Grill (42) and Ovivi's
-- Restaurant (18) — with the Gold Coast Comedy proxy left at 0 shows.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database. (The per-venue clubs are created
-- by the scraper at run time, not by this migration.)

-- 1. The roving-producer proxy club (HIDDEN — visible=false). Guard on name OR
--    google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Gold Coast Comedy Club',
       '3333 NE 32nd Ave',
       'https://www.eventbrite.com/o/gold-coast-comedy-26218736367',
       'Fort Lauderdale', 'FL', '33308',
       'America/New_York', 'US', 'club',
       'ChIJHQY89iQB2YgRgC11OGz9L9g',
       false, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Gold Coast Comedy Club'
     OR google_place_id = 'ChIJHQY89iQB2YgRgC11OGz9L9g'
);

-- 2. Eventbrite ORGANIZER source: source_url CONTAINS /o/ (activates per-venue
--    routing); eventbrite_id holds the organizer id. Guard with NOT EXISTS on
--    (club_id, scraper_key) — no unique constraint beyond the PK.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com/o/gold-coast-comedy-26218736367',
       '26218736367', 0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Gold Coast Comedy Club' OR c.google_place_id = 'ChIJHQY89iQB2YgRgC11OGz9L9g')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  );
