-- Onboard Music City Starfactory (formerly Music City San Francisco), San Francisco, CA - TASK-3210.
--
-- Music City Starfactory is a multi-kind music-themed hotel/hostel + live-music venue at
-- 1355 Bush St, San Francisco. Its own site (musiccitysf.com) advertises "five stages
-- featuring live music, DJs, comedy, and more" and explicitly lists "Stand Up Comedy"
-- among its recurring programming (Open Mics, DJ sets, Karaoke, Rock shows, Stand Up
-- Comedy). Every event links out to a single Eventbrite organizer, Music City San
-- Francisco (12803819712).
--
-- That ONE organizer feed is mixed-use: music acts named after the band/DJ/series (e.g.
-- "Jazz Tuesdays", "Latin Sundays", "Eclectic Fridays", "Rock and Country Wednesdays",
-- "The Motown Sound") alongside the venue's comedy. Because the music titles are
-- unpredictable, an exclude list can't isolate the comedy, so the source carries an
-- `include_title_patterns` comedy allowlist (TASK-3205 added include semantics to the
-- eventbrite scraper): the scraper keeps ONLY events whose title matches
-- comedy / stand-up / comedian / open mic and drops the music.
--
-- Organizer mode: the eventbrite scraper groups the organizer's (comedy) events by
-- Eventbrite venue and attaches each show to the matching per-venue club. The Eventbrite
-- API venue "Music City" / "Music City Starfactory" (San Francisco, CA) matches this
-- club, so the comedy shows attach here.
--
-- Idempotent: NOT-EXISTS-guarded INSERTs keyed on google_place_id / name so the migration
-- no-ops where the rows already exist and reproduces on a fresh DB.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Music City Starfactory', '1355 Bush St, San Francisco, CA 94109',
    'https://www.musiccitysf.com/',
    'San Francisco', 'CA', '94109', 'America/Los_Angeles', 'US', 'club',
    'ChIJo6G1OpyBhYARNibbIVdNA7E', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJo6G1OpyBhYARNibbIVdNA7E'
       OR name = 'Music City Starfactory'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/music-city-san-francisco-12803819712',
    '12803819712',
    TRUE,
    0,
    '{"include_title_patterns": ["comedy", "stand[ -]?up", "comedian", "open mic"]}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJo6G1OpyBhYARNibbIVdNA7E' OR c.name = 'Music City Starfactory')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
