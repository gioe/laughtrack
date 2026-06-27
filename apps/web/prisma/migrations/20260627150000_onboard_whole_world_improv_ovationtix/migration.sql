-- Onboard Whole World Improv Theatre (Atlanta, GA) — TASK-3366,
-- objective #12 discover-comedy-venues near Atlanta 30303.
--
-- Whole World Improv Theatre is an all-improv comedy theater with a busy recurring
-- calendar (Classic Improv Show, Thursday Happy Hour, Laughtopia, Musical Mayhem,
-- Whole World Improv Cup, Black Voices Unscripted, El Show Improvisado, ...).
-- Its own site (wholeworldtheatre.com) links ticketing to accesso/OvationTix
-- client 36156 (ci.ovationtix.com/36156/production/{id}). The existing generic
-- `ovationtix` scraper handles it: source_url = the server-rendered calendar
-- web.ovationtix.com/trs/cal/36156, ovationtix_id = 36156.
--
-- Wrinkle: the OvationTix calendar mixes the public improv SHOWS with improv
-- CLASSES (Adult Beginner/Intermediate, One Day Workshop, Improvius Prime) and a
-- "Kids Camp 2026". These are not public comedy shows. The ovationtix scraper
-- applies metadata.exclude_title_patterns only when comedy_filter is enabled, so
-- this source sets comedy_filter=true plus exclude_title_patterns=['CLASSES','Kids
-- Camp']. Verified that all 8 public improv series survive the comedy keyword
-- check (zero real-show loss) while the classes/camp are dropped.
--
-- Fixed venue (its own theater) -> visible=true.
--
-- Verification: `make scrape-club-id ID=<club_id>` scraped 84 shows across the 8
-- recurring improv series, classes/camp excluded (club 11461, source 7029).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Whole World Improv Theatre',
       '1216 Spring St NW, Atlanta, GA 30309',
       'https://www.wholeworldtheatre.com',
       'Atlanta', 'GA', '30309',
       'America/New_York', 'US', 'club',
       'ChIJ79dGvlsE9YgRfB567iz9Ht0',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Whole World Improv Theatre'
     OR google_place_id = 'ChIJ79dGvlsE9YgRfB567iz9Ht0'
);

-- 2. The ovationtix scraping source (server-rendered calendar + client id, plus a
-- comedy_filter + exclude_title_patterns to drop improv classes / kids camp).
-- platform 'ovationtix' is a curated enum value; the scraper reads the client id
-- from ovationtix_id. Locate the club by name OR google_place_id for idempotency.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, ovationtix_id, priority, enabled, metadata)
SELECT c.id, 'ovationtix', 'ovationtix',
       'https://web.ovationtix.com/trs/cal/36156',
       '36156',
       0, true,
       jsonb_build_object(
         'comedy_filter', true,
         'exclude_title_patterns', jsonb_build_array('CLASSES', 'Kids Camp')
       )
FROM clubs c
WHERE (c.name = 'Whole World Improv Theatre' OR c.google_place_id = 'ChIJ79dGvlsE9YgRfB567iz9Ht0')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'ovationtix'
  );
