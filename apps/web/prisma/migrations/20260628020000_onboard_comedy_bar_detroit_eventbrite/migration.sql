-- Onboard The Comedy Bar - Detroit (Detroit, MI) — TASK-3374,
-- objective #12 discover-comedy-venues near Detroit 48226.
--
-- The Comedy Bar - Detroit is an active all-comedy stand-up club (lower level of
-- the Norwood Theater, 6531 Woodward Ave) running national headliners + local
-- showcases every weekend. Its own site (comedybar.com/detroit) embeds the
-- Eventbrite widget for organizer "The Comedy Bar - Detroit"
-- (organizer id 32281982053); every show tickets through Eventbrite. The 49
-- live events are all named stand-up sets (Shayne Smith, Leah Lamarr, Andy
-- Haynes, Marcus Monroe, Ed Bassmaster, ...), so no comedy_filter is needed.
--
-- Wiring — eventbrite SINGLE-VENUE mode (convention #192/#252, mirrors TASK-3367
-- Uptown Comedy Corner): the organizer feed exposes a single Eventbrite venue id
-- 250922873 for this fixed Woodward Ave room. Using single-venue mode
-- (source_url omits /o/, eventbrite_id = the venue id) attaches all 49 shows
-- directly to this one visible club via /v3/venues/250922873/events/ — no
-- per-venue auto-club fragmentation, and the club keeps a stable name distinct
-- from the unrelated "The Comedy Bar Chicago" / "The Comedy Bar - Pittsburgh"
-- rows. Fixed venue -> visible=true.
--
-- Verification: a single-venue-mode scrape of venue id 250922873 returned 49
-- comedy shows, each show_page_url an eventbrite.com/e/ ticket page; a real
-- `make scrape-club-id ID=<club_id>` persisted them onto this one club.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Comedy Bar - Detroit',
       '6531 Woodward Ave, Detroit, MI 48202',
       'https://comedybar.com/detroit',
       'Detroit', 'MI', '48202',
       'America/Detroit', 'US', 'club',
       'ChIJNUFURpTTJIgRXONmJARn0Y0',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'The Comedy Bar - Detroit'
     OR google_place_id = 'ChIJNUFURpTTJIgRXONmJARn0Y0'
);

-- 2. The eventbrite SINGLE-VENUE scraping source (source_url omits /o/ and
-- eventbrite_id is the Eventbrite VENUE id, so /v3/venues/250922873/events/
-- routes every show to this one club). platform 'eventbrite' is a curated enum
-- value; the scraper reads the id from eventbrite_id. Locate the club by name OR
-- google_place_id for idempotency.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com',
       '250922873',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'The Comedy Bar - Detroit' OR c.google_place_id = 'ChIJNUFURpTTJIgRXONmJARn0Y0')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
