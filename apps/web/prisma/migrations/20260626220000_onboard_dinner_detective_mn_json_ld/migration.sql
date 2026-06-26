-- Onboard The Dinner Detective — Minneapolis + St. Paul (MN) — TASK-3327,
-- objective #8 discover-comedy-venues near Twin Cities 55401.
--
-- The Dinner Detective is a national franchise of interactive true-crime murder
-- mystery comedy dinner shows. Each location has its own marketing site at
-- thedinnerdetective.com/<city>/ whose showtimes page —
--   https://www.thedinnerdetective.com/<city>/murder-mystery-tickets-showtimes/
-- — embeds one `<script type="application/ld+json">` `TheaterEvent` block per
-- upcoming show (name, startDate with offset, offers/price, and a buy URL on
-- the Cloudflare-challenged tickets-<city>.thedinnerdetective.com booking
-- subdomain). The venue's OWN site serves these blocks at HTTP 200, so the
-- generic `json_ld` scraper reads them directly — no need to touch the
-- bot-protected booking subdomain.
--
-- `TheaterEvent` is a schema.org subtype of Event; the json_ld extractor's
-- case-insensitive "...event..." match already accepts it (it is not in the
-- eventseries/eventlisting/eventschedule exclude set). scraper_key = 'json_ld',
-- source_url = the per-city showtimes page.
--
-- Fixed VENUEs (each runs inside a named hotel) -> visible=true. metadata '{}'.
--
-- Verification: validated end-to-end against the LIVE sites — Minneapolis
-- scraped 5 shows ($73.95, dates through 2026-08). St. Paul currently has NO
-- upcoming shows posted (its showtimes page renders 0 TheaterEvent blocks and a
-- "no upcoming shows" message), so a scrape returns 0 today — that is the
-- genuine current state, not a scraper failure; the nightly run will populate
-- it when the next show is posted (the json_ld wiring is proven by the
-- identical Minneapolis sibling).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue clubs (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Dinner Detective Minneapolis',
       '1500 Washington Avenue South, Inside Courtyard Minneapolis Downtown',
       'https://www.thedinnerdetective.com/minneapolis/',
       'Minneapolis', 'MN', '55454',
       'America/Chicago', 'US', 'club',
       'ChIJ1dg_iZsys1IRxSl2vqBNtPM',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'The Dinner Detective Minneapolis'
     OR google_place_id = 'ChIJ1dg_iZsys1IRxSl2vqBNtPM'
);

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Dinner Detective St. Paul',
       '2201 Burns Ave, Inside DoubleTree by Hilton St. Paul East',
       'https://www.thedinnerdetective.com/st-paul/',
       'St. Paul', 'MN', '55119',
       'America/Chicago', 'US', 'club',
       'ChIJ2QT0RsHX94cR76Mrl0QjV7E',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'The Dinner Detective St. Paul'
     OR google_place_id = 'ChIJ2QT0RsHX94cR76Mrl0QjV7E'
);

-- 2. The json_ld scraping sources (each city's showtimes page). platform is the
-- curated `ScrapingPlatform` enum; json_ld is not a member, so use 'custom'.
-- The scraper is resolved by scraper_key ('json_ld'), not by platform. Locate
-- the club by name OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'json_ld',
       'https://www.thedinnerdetective.com/minneapolis/murder-mystery-tickets-showtimes/',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'The Dinner Detective Minneapolis' OR c.google_place_id = 'ChIJ1dg_iZsys1IRxSl2vqBNtPM')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'json_ld',
       'https://www.thedinnerdetective.com/st-paul/murder-mystery-tickets-showtimes/',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'The Dinner Detective St. Paul' OR c.google_place_id = 'ChIJ2QT0RsHX94cR76Mrl0QjV7E')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
