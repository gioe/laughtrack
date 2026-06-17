-- Onboard MEDIUM-tier comedy venues near 90012 — discover-comedy-venues (2026-06-17), TASK-2944 follow-up
--
-- Companion to 20260620011000_onboard_discover_90012_high_tier. Onboards the
-- comedy-worthy MEDIUM-tier venues from the 90012 sweep. Datasource per venue:
--   crowdwork: WGIS (World's Greatest Improv School). eventbrite organizer:
--   Jam in the Van, Chatterbox. eventbrite venue mode (auto-created then
--   consolidated): Hotel Zoso (The Club Downtown). the_events_calendar (tribe,
--   currently 0 upcoming -- will populate when the venues post dates): Yeah Mon
--   Comedy Lounge, Tao Comedy Studio.
--
-- Also corrects VENPROV | Ventura Improv's website (the discovery sweep recorded
-- a magic-school URL; the real site is venturaimprov.com).
--
-- NOT in this migration (intentionally): Que Sera (tockify) and The Jazzy Wishbone
-- (wix) were wired then DISABLED -- their calendars are music-first and the
-- tockify/wix scrapers lack a comedy genre filter (tracked by TASK-2952);
-- re-enable once that lands.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; the VENPROV update is conditional.
-- Verified as a 0-row no-op against prod. Generated from prod state.


INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'WGIS - World''s Greatest Improv School', '1615 N Vermont Ave, Los Angeles, CA 90027, USA', 'https://wgimprovschool.com/', 'Los Angeles', 'CA', '90027', 'US', 'club', 'ChIJR-1x_rfBwoAR03r0LQWcIgs', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'WGIS - World''s Greatest Improv School');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Jam in the Van', '3384 Motor Ave, Los Angeles, CA 90034, USA', 'http://jaminthevan.com/', 'Los Angeles', 'CA', '90034', 'US', 'club', 'ChIJrdkHZwm7woARDGKBGb5IYo4', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Jam in the Van');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Chatterbox', '943 N Citrus Ave, Covina, CA 91722, USA', '', 'Covina', 'CA', '91722', 'US', 'club', 'ChIJWWXWjmgow4ARcTJXxz_xoUM', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Chatterbox');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Yeah Mon Comedy Lounge', '7551 Melrose Ave, Los Angeles, CA 90046, USA', 'https://yeahmoncomedylounge.com/', 'Los Angeles', 'CA', '90046', 'US', 'club', 'ChIJl4fXkM-_woARj4z0PJqdSjA', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Yeah Mon Comedy Lounge');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Tao Comedy Studio', '131 South Western Avenue between 1st and, W 2nd St, Los Angeles, CA 90004, USA', 'http://taocomedystudio.com/', 'Los Angeles', 'CA', '90004', 'US', 'club', 'ChIJ61Squi65woAR1T-9_xK_XaQ', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Tao Comedy Studio');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Hotel Zoso', '150 S Indian Canyon Dr', '', 'Palm Springs', 'CA', '92262', 'US', 'club', 'ChIJD2VeFaQb24ARoU9ZSyUrfaY', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Hotel Zoso');



INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'tribe_events'::"ScrapingPlatform", 'the_events_calendar', 'https://taocomedystudio.com/wp-json/tribe/events/v1/events', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Tao Comedy Studio'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'crowdwork'::"ScrapingPlatform", 'crowdwork', 'https://crowdwork.com/api/v2/wgis/shows', NULL, NULL, 0, TRUE, '{"rails_to_iana":true,"default_timezone":"America/Los_Angeles"}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'WGIS - World''s Greatest Improv School'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'crowdwork');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'tribe_events'::"ScrapingPlatform", 'the_events_calendar', 'https://yeahmoncomedylounge.com/wp-json/tribe/events/v1/events', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Yeah Mon Comedy Lounge'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/45377795513', '45377795513', NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Jam in the Van'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/12718305272', '12718305272', NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Chatterbox'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com', '276777263', NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Hotel Zoso'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');



UPDATE clubs SET website = 'https://venturaimprov.com/'
WHERE name = 'VENPROV | Ventura Improv' AND website LIKE '%thomagic%';
