-- Onboard The Guild Theater (Sacramento, CA) via the existing eventbrite scraper - TASK-3233.
--
-- The Guild Theater is a historic performing-arts theater at 2828 35th St in
-- Sacramento's Oak Park district, operated by St. HOPE. Its own site
-- (guildtheater.com -> www.sthope.org/guild-theater-home) links every upcoming
-- show out to a single Eventbrite organizer, "Guild Theater"
-- (https://www.eventbrite.com/o/guild-theater-3748052993). Stand-up comedy is
-- confirmed on that feed: "Comedy Night At the Guild Theater" (21+, headliner
-- DC Ervin), whose JSON-LD location is exactly The Guild Theater,
-- 2828 35th Street, Sacramento, CA 95817 (verified 2026-06-24).
--
-- MIXED-USE FEED: the organizer feed is not comedy-only -- it also carries
-- non-music, non-comedy performing-arts events that the eventbrite scraper's
-- built-in Music-category filter does NOT drop (e.g. "Dusty Baker Author Talk"),
-- alongside music tributes ("Tutti Fruitti: A Tribute to Little Richard"). To
-- keep ONLY comedy off this mixed feed, the source carries an
-- `include_title_patterns` comedy allowlist (TASK-3205 include semantics): the
-- scraper keeps only events whose title matches comedy / stand-up / comedian /
-- open mic and drops everything else.
--
-- ORGANIZER MODE: the eventbrite scraper groups the organizer's (comedy) events
-- by Eventbrite venue and attaches each show to the matching per-venue club. The
-- Eventbrite API venue "The Guild Theater" (Sacramento, CA) matches this club's
-- name + location, so the comedy shows attach here (no duplicate per-venue club;
-- convention #192). visible = TRUE because this is a single fixed physical venue.
--
-- Idempotent: NOT-EXISTS-guarded INSERTs keyed on google_place_id / name so the
-- migration no-ops where the rows already exist and reproduces on a fresh DB.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'The Guild Theater', '2828 35th St, Sacramento, CA 95817',
    'http://www.guildtheater.com/',
    'Sacramento', 'CA', '95817', 'America/Los_Angeles', 'US', 'club',
    'ChIJj0gnIV7QmoARFg13hhCgO5w', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJj0gnIV7QmoARFg13hhCgO5w'
       OR name = 'The Guild Theater'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/guild-theater-3748052993',
    '3748052993',
    TRUE,
    0,
    '{"include_title_patterns": ["comedy", "stand[ -]?up", "comedian", "open mic"]}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJj0gnIV7QmoARFg13hhCgO5w' OR c.name = 'The Guild Theater')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
