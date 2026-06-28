-- Onboard Planet Ant (Hamtramck, MI) — TASK-3377,
-- objective #12 discover-comedy-venues near Detroit 48226.
--
-- Planet Ant Theatre (2320 Caniff Ave) is a long-running Detroit comedy/improv
-- house. discover-comedy-venues surfaced the address as "The Independent Comedy
-- Club at Planet Ant" (a comedian-run stand-up series at the venue), but that
-- stand-up series has no findable Eventbrite organizer or working website and is
-- not bookable online. What IS live at this address is Planet Ant Theatre's own
-- Eventbrite organizer ("Planet Ant Theatre, Inc.", organizer id 26913802005):
-- 57 comedy shows — recurring improv house teams (Monday Night Improv, The
-- Thursday Show, Mixtape Friendship 5000, Planet Ant Colony Fest) plus sketch
-- (Tiny Idea Live!). The operator confirmed onboarding the venue as "Planet Ant"
-- (the accurate, bookable entity) rather than the unscrapable stand-up sub-brand.
--
-- Wiring — eventbrite SINGLE-VENUE mode (convention #192/#252/#271): the organizer
-- feed tags shows across several Planet Ant venue ids (Black Box variants + Ant
-- Hall), so organizer mode would fragment them into multiple per-venue auto-clubs.
-- Single-venue mode (source_url omits /o/, eventbrite_id = the organizer id) makes
-- the /v3/venues/<id> probe 404 and fall back to /organizers/<id>, routing every
-- show onto this one visible club.
--
-- Comedy filter: the same organizer feed also carries non-comedy straight theater
-- ("THEATER | The Hours Between") and a burlesque showcase. include_title_patterns
-- keeps only comedy (the venue prefixes shows IMPROV|/SKETCH|; the allowlist also
-- admits future comedy/stand-up/comedian-titled shows) and drops the 8 theater + 1
-- burlesque events. Verified: 66 raw events -> 57 comedy shows after the filter.
--
-- Verification: a single-venue-mode scrape with this filter returned 57 comedy
-- shows; a real `make scrape-club-id ID=<club_id>` persisted them onto this one
-- club, each show_page_url an eventbrite.com/e ticket page. Fixed venue -> visible.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Planet Ant',
       '2320 Caniff Ave, Hamtramck, MI 48212',
       'https://www.planetant.com',
       'Hamtramck', 'MI', '48212',
       'America/Detroit', 'US', 'club',
       'ChIJCbxFJSzTJIgRYlou9n4QtMQ',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Planet Ant'
     OR google_place_id = 'ChIJCbxFJSzTJIgRYlou9n4QtMQ'
);

-- 2. The eventbrite SINGLE-VENUE scraping source with a comedy include filter.
-- source_url omits /o/ and eventbrite_id is the organizer id, so every organizer
-- show routes to this one club via the venue->organizer 404 fallback;
-- include_title_patterns keeps only comedy (improv/sketch/comedy/stand-up). Locate
-- the club by name OR google_place_id for idempotency.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com',
       '26913802005',
       0, true,
       '{"include_title_patterns": ["improv", "sketch", "comedy", "stand[ -]?up", "comedian"]}'::jsonb
FROM clubs c
WHERE (c.name = 'Planet Ant' OR c.google_place_id = 'ChIJCbxFJSzTJIgRYlou9n4QtMQ')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
