-- Onboard St. Louis comedy venues discovered under objective 7 (TASK-3292 follow-ups).
-- Idempotent data migration: clubs guarded by ON CONFLICT(name), scraping_sources
-- guarded by NOT EXISTS(club_id, scraper_key). No-ops where rows already exist
-- (already applied directly to prod 2026-06-25); reproduces on fresh DBs.
--
-- 5 venues wired to existing scrapers; 8 venue-identity rows with NO scraper
-- (hidden) for venues whose comedy is not machine-scrapable today.

-- ============ Clubs ============
-- Wired venues (visible; the web app hides them until they have upcoming shows).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status) VALUES
  ('The Improv Shop', '3960 Chouteau Ave, St. Louis, MO 63110', 'http://www.theimprovshop.com/', 'St. Louis', 'MO', '63110', 'America/Chicago', 'US', 'club', 'ChIJ5Wr7oNW02IcRzk8Iwp7apRI', true, 'active'),
  ('KJ''s Bar and Grill', '5300 N Broadway, St. Louis, MO 63147', '', 'St. Louis', 'MO', '63147', 'America/Chicago', 'US', 'club', 'ChIJUeqx9JNM34cRWAw4h1IEEfk', true, 'active'),
  ('Graffiti Loft', '1802 S 9th St, St. Louis, MO 63104', 'http://www.graffitiloft.com/', 'St. Louis', 'MO', '63104', 'America/Chicago', 'US', 'club', 'ChIJ1eBIa6Sz2IcRDBfDtvFavqA', true, 'active'),
  ('CBA Event Center', '2619 Washington Ave, St. Louis, MO 63103', '', 'St. Louis', 'MO', '63103', 'America/Chicago', 'US', 'club', 'ChIJ-65Dc3Wz2IcRajlvW2QkctY', true, 'active'),
  ('HollyLou Entertainment', '155 S Florissant Rd, Ferguson, MO 63135', 'http://hollylouent.rocks/', 'Ferguson', 'MO', '63135', 'America/Chicago', 'US', 'club', 'ChIJm5NoOuA334cRLWZhfKaQdPM', true, 'active')
ON CONFLICT (name) DO NOTHING;

-- Venue-identity rows, NO scraper (hidden; recorded so future discovery dedups
-- against them and they can be onboarded later).
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status) VALUES
  ('Twisted Improv', '314 S Clay Ave, Kirkwood, MO 63122', 'http://www.ktg-onstage.org/', 'Kirkwood', 'MO', '63122', 'America/Chicago', 'US', 'club', 'ChIJYd-J-i3M2IcRVmj2aEMU89s', false, 'active'),
  ('Anti-Barrr Comedy Joint', '141 S Main St, Waterloo, IL 62298', '', 'Waterloo', 'IL', '62298', 'America/Chicago', 'US', 'club', 'ChIJ8WPGnI-92IcRIW9T4T6wjFM', false, 'active'),
  ('The Heavy Anchor', '5226 Gravois Ave, St. Louis, MO 63116', 'http://theheavyanchor.com/', 'St. Louis', 'MO', '63116', 'America/Chicago', 'US', 'club', 'ChIJ4YNx1M-12IcR994iWMwHKWA', false, 'active'),
  ('Purple Quarters', '4170 Manchester Ave, St. Louis, MO 63110', 'https://www.purplequartersstl.com/', 'St. Louis', 'MO', '63110', 'America/Chicago', 'US', 'club', 'ChIJk7dzRFm12IcR-kPYLncgksc', false, 'active'),
  ('Greenfinch Theater & Dive', '2525 S Jefferson Ave, St. Louis, MO 63104', 'http://greenfinchstl.com/', 'St. Louis', 'MO', '63104', 'America/Chicago', 'US', 'club', 'ChIJgeXKaKCz2IcRs2vKzwSsTlU', false, 'active'),
  ('Westport Playhouse', '635 W Port Plaza Dr, St. Louis, MO 63146', 'https://thewestportplayhouse.com/', 'St. Louis', 'MO', '63146', 'America/Chicago', 'US', 'club', 'ChIJS-0xaHky34cRH4PKj0arEBg', false, 'active'),
  ('Hot Java Bar', '4193 Manchester Ave, St. Louis, MO 63110', 'http://hotjava.bar/', 'St. Louis', 'MO', '63110', 'America/Chicago', 'US', 'club', 'ChIJhT_Nq9612IcRwgwqWUHIWW4', false, 'active'),
  ('HandleBar', '4127 Manchester Ave, St. Louis, MO 63110', 'http://www.handlebarstl.com/', 'St. Louis', 'MO', '63110', 'America/Chicago', 'US', 'club', 'ChIJt4ms6-i02IcRePJV_wR2Ll4', false, 'active')
ON CONFLICT (name) DO NOTHING;

-- ============ Scraping sources (wired venues only) ============
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'tribe_events'::"ScrapingPlatform", 'the_events_calendar', 'https://theimprovshop.com/wp-json/tribe/events/v1/events', NULL, 0, true, '{}'::jsonb
FROM clubs c WHERE c.name = 'The Improv Shop'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/89203190763', '89203190763', 0, true, '{}'::jsonb
FROM clubs c WHERE c.name = 'KJ''s Bar and Grill'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/graffiti-loft-121148654563', '121148654563', 0, true, '{"include_title_patterns": ["comedy", "stand[ -]?up", "comedian", "corduroy lounge", "hazy brunch"]}'::jsonb
FROM clubs c WHERE c.name = 'Graffiti Loft'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/black-ceasar-9372140944', '9372140944', 0, true, '{"include_title_patterns": ["comedy", "stand[ -]?up", "comedian", "comedy jam"]}'::jsonb
FROM clubs c WHERE c.name = 'CBA Event Center'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/venues/143661759/events/', '143661759', 0, true, '{"include_title_patterns": ["comedy", "stand[ -]?up", "comedian", "laughs?", "jokes"]}'::jsonb
FROM clubs c WHERE c.name = 'HollyLou Entertainment'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
