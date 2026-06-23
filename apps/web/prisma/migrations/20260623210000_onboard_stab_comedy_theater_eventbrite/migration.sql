-- Onboard STAB! Comedy Theater (Sacramento, CA) via the existing eventbrite scraper - TASK-3199.
--
-- STAB! is a fixed comedy venue at 1710 Broadway, Sacramento. Its Wix site
-- (stabcomedytheater.com) hosts a /shows and /calendar page, but the Wix Events
-- and Wix Bookings apps on the site are effectively empty (1 cancelled 2018
-- "STAB! Comedy Podcast" event; 1 default Wix demo bookings service). The live
-- stand-up/improv shows are ticketed through a single Eventbrite organizer,
-- "STAB! Comedy Theater" (organizer id 35284584163) — each show page on the Wix
-- site links to that organizer's Eventbrite event (e.g. TheEverythingShow /
-- thestabshow vanity subdomains both resolve to events under org 35284584163).
--
-- This wires to the generic `eventbrite` scraper in organizer mode (source_url
-- contains /o/): it fetches the organizer's events with venue expansion and
-- attaches each show to the matching per-venue club. The organizer's
-- "STAB! Comedy Theater" venue (1710 Broadway) matches this club exactly, so its
-- shows attach here. STAB is its own fixed venue, so visible = TRUE.
--
-- NOTE (verified 2026-06-23): a real scrape of the organizer feed produced
-- multiple upcoming comedy shows attached to this club.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'STAB! Comedy Theater', '1710 Broadway, Sacramento, CA 95818, USA',
    'http://www.stabcomedytheater.com/',
    'Sacramento', 'CA', '95818', 'America/Los_Angeles', 'US', 'club',
    'ChIJVWteSx_RmoARUdmyoYfxKBw', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJVWteSx_RmoARUdmyoYfxKBw'
       OR name = 'STAB! Comedy Theater'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/stab-comedy-theater-35284584163',
    '35284584163',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJVWteSx_RmoARUdmyoYfxKBw' OR c.name = 'STAB! Comedy Theater')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
