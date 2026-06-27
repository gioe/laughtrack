-- Onboard The Dinner Detective Cincinnati (Covington, KY) — TASK-3346,
-- objective #10 discover-comedy-venues near Cincinnati 45202/41011.
--
-- Same national franchise + recipe as the Minneapolis/St. Paul onboard
-- (TASK-3327): an interactive true-crime murder-mystery comedy dinner show whose
-- own marketing site at thedinnerdetective.com/<city>/ exposes a showtimes page —
--   https://www.thedinnerdetective.com/cincinnati/murder-mystery-tickets-showtimes/
-- — embedding one `<script type="application/ld+json">` `TheaterEvent` block per
-- upcoming show (name, startDate with -04:00 offset, location, offers, and a buy
-- URL on the Cloudflare-challenged tickets-cnc.thedinnerdetective.com booking
-- subdomain). The venue's OWN site serves these blocks at HTTP 200, so the
-- generic `json_ld` scraper reads them directly — no need to touch the
-- bot-protected booking subdomain.
--
-- `TheaterEvent` is a schema.org subtype of Event; the json_ld extractor's
-- case-insensitive "...event..." match already accepts it. scraper_key='json_ld',
-- source_url = the per-city showtimes page, platform 'custom' (json_ld is not a
-- ScrapingPlatform enum member; the scraper is resolved by scraper_key).
--
-- The Cincinnati show runs inside Embassy Suites by Hilton Cincinnati Rivercenter
-- (10 E Rivercenter Blvd, Covington KY 41011 — Eastern time). Google lists the
-- venue under a downtown-Cincinnati address, but the JSON-LD location (used here)
-- is the actual hotel. Fixed VENUE -> visible=true. metadata '{}'.
--
-- Verification: validated end-to-end against the LIVE site — scraped 2 shows
-- (Sat Jul 11 & Jul 25, 2026, 6:00 PM ET).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Dinner Detective Cincinnati',
       '10 E Rivercenter Blvd, Inside Embassy Suites by Hilton Cincinnati Rivercenter',
       'https://www.thedinnerdetective.com/cincinnati/',
       'Covington', 'KY', '41011',
       'America/New_York', 'US', 'club',
       'ChIJtz6DdlGxQYgRnMRzHj37bq8',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'The Dinner Detective Cincinnati'
     OR google_place_id = 'ChIJtz6DdlGxQYgRnMRzHj37bq8'
);

-- 2. The json_ld scraping source (the city's showtimes page). Locate the club by
-- name OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'json_ld',
       'https://www.thedinnerdetective.com/cincinnati/murder-mystery-tickets-showtimes/',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'The Dinner Detective Cincinnati' OR c.google_place_id = 'ChIJtz6DdlGxQYgRnMRzHj37bq8')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
