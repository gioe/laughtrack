-- Onboard Uptown Comedy Corner (Forest Park, GA) — TASK-3367,
-- objective #12 discover-comedy-venues near Atlanta 30303.
--
-- Uptown Comedy Corner is an established all-comedy club with a full weekly
-- recurring stand-up calendar (Saturday Night Live Comedy, Sunset Sundays,
-- Funny First Fridays, Friday Night Traffic Jam, Date Night Tuesdays open mic,
-- Monday Night Spotlight, Thursday Night Open Mic). Its own site
-- (uptowncomedy.net) tickets every show via its Eventbrite organizer
-- "Atlanta's Original Uptown Comedy Corner" (organizer id 19121665208).
--
-- Wiring — eventbrite SINGLE-VENUE mode (convention #192/#252): organizer mode
-- (source_url containing /o/) split this organizer's shows across per-venue
-- auto-clubs because the organizer tags its own Forest Park room with the
-- Eventbrite venue name "4730 Frontage Rd" (which does not match the club name
-- "Uptown Comedy Corner"), plus it runs a few shows at a second venue
-- (Traditions Global Cuisine, Morrow GA). To keep one clean visible club, this
-- source uses single-venue mode: source_url='https://www.eventbrite.com' (omit
-- /o/) with eventbrite_id=organizer id. The venue-probe GET /v3/venues/19121665208
-- returns 404, so the venue->organizer auto-fallback fires safely and routes
-- EVERY organizer show onto the one onboarded club (no per-venue auto-club). The
-- handful of Uptown-produced shows at Traditions collapse onto the Uptown club
-- too (accepted producer-attribution tradeoff vs. fragmentation, per #192).
--
-- All-comedy organizer -> no comedy_filter. Fixed venue -> visible=true.
--
-- Verification: `make scrape-club-id ID=<club_id>` scraped 15 shows onto the
-- single club with NO duplicate per-venue auto-club created (club 11462,
-- source 7030).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Uptown Comedy Corner',
       '4730 Frontage Rd, Forest Park, GA 30297',
       'https://www.uptowncomedy.net',
       'Forest Park', 'GA', '30297',
       'America/New_York', 'US', 'club',
       'ChIJpQS7OY4E9YgRx3k3Q_6dwG8',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Uptown Comedy Corner'
     OR google_place_id = 'ChIJpQS7OY4E9YgRx3k3Q_6dwG8'
);

-- 2. The eventbrite SINGLE-VENUE scraping source (source_url omits /o/, so every
-- organizer show routes to this one club via the venue->organizer 404 fallback).
-- platform 'eventbrite' is a curated enum value; the scraper reads the id from
-- eventbrite_id. Locate the club by name OR google_place_id for idempotency.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com',
       '19121665208',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Uptown Comedy Corner' OR c.google_place_id = 'ChIJpQS7OY4E9YgRx3k3Q_6dwG8')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
