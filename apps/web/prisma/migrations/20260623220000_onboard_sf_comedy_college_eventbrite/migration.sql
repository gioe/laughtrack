-- Onboard San Francisco Comedy College via the existing eventbrite scraper - TASK-3219.
--
-- CONTEXT: This task started as "Onboard scraper for The Hub RWC (Redwood City,
-- CA)", a Wix-built event/restaurant venue (thehubrwc.com) discovered near SF
-- 94101. The Hub's own site is a mixed-use bar/games/live-music venue: its page
-- set is MUSIC / GAMES / FILM / OPEN MIC / MAGIC / BURLESQUE / BANDS / JAM NIGHT
-- / DJ, with an EVENT CALENDAR page backed by a Wix "Google Event Calendar" TPA
-- widget (NOT the scrapable Wix Events app). The word "comedy" appears nowhere
-- on the site, so The Hub is not a comedy venue in its own right and has no
-- scrapable comedy calendar of its own.
--
-- WHO HOSTS THE COMEDY: stand-up at The Hub is produced by an external roving
-- producer, "San Francisco Comedy College" (Eventbrite organizer id
-- 13734612973), e.g. "Fog City Funnies: Stand Up Comedy in Redwood City" — a
-- 12-comedian stand-up show at The Hub RWC (2650 Broadway), ticketed on
-- Eventbrite. That organizer is a comedy SCHOOL that also runs shows at other
-- venues, so we onboard the ORGANIZER (not The Hub directly) and let the
-- eventbrite scraper's organizer mode route each show to its own per-venue club
-- (The Hub RWC among them). The proxy is therefore visible = FALSE (hidden
-- roving-producer synthetic; real shows surface under auto-created per-venue
-- clubs).
--
-- MIXED FEED: the organizer's Eventbrite feed mixes free "Intro to Stand Up"
-- CLASSES with the actual stand-up shows, so metadata.exclude_classes = true
-- keeps the class/course/workshop listings out (the shared eventbrite scraper's
-- built-in class title patterns).
--
-- NOTE (verified 2026-06-23): a real scrape of organizer 13734612973 validated
-- the Eventbrite token and fetched the live feed. At this moment the organizer
-- has exactly ONE live event — a "Free Stand Up Comedy Intro Class" (no venue) —
-- which exclude_classes correctly drops (0 shows kept). The Hub RWC comedy show
-- (Fog City Funnies, 2026-06-13) has already passed. This source is wired so
-- that the NEXT Hub RWC (or other-venue) stand-up show the organizer posts is
-- picked up automatically and attached to its per-venue club on the next
-- nightly run (deferred-attach, same pattern as TASK-3192 Clayton Club Saloon).

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, visible, status
)
SELECT
    'San Francisco Comedy College',
    '414 Mason St, San Francisco, CA 94102, USA',
    'https://www.eventbrite.com/o/san-francisco-comedy-college-13734612973',
    'San Francisco', 'CA', '94102', 'America/Los_Angeles', 'US', 'club',
    FALSE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs WHERE name = 'San Francisco Comedy College'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/san-francisco-comedy-college-13734612973',
    '13734612973',
    TRUE,
    0,
    jsonb_build_object('exclude_classes', true),
    NOW(),
    NOW()
FROM clubs c
WHERE c.name = 'San Francisco Comedy College'
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
