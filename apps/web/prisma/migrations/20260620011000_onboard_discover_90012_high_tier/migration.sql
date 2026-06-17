-- Onboard 13 HIGH-tier comedy venues near 90012 — discover-comedy-venues (2026-06-17), TASK-2944 follow-up
--
-- Reproduces the live onboarding of 13 venues surfaced by the discover-comedy-venues
-- sweep of ZIP 90012 (100 mi). Each club is created (if absent) and wired to an
-- existing generic scraper. Datasource per venue:
--   tixr (group-events API fallback, group id in metadata): The Upstairs (2391), The Nitecap (1357)
--     -- Tixr detail pages are DataDome/capsolver-blocked; the group-events JSON API is used instead.
--   eventbrite organizer mode (source_url has /o/): Lyric Hyperion, Pack Theater, Zebra Room, Hollywood Comedy
--   eventbrite venue mode (source_url = eventbrite.com, eventbrite_id = venue id): Astronaut City,
--     Rock Gallery, Hideaway Cafe, Best Comedy Club Near Me -- these were auto-created/resolved by the
--     organizer-mode scraper, then consolidated to clean names + google_place_id.
--   the_events_calendar (WordPress tribe REST): FanaticSalon
--   wix_events (events widget component id): JEST Improv
--   json_ld (events page): The Welcome Room
--
-- Lyric Hyperion: club_aliases map the organizer's venue-name variants ("Lyric Hyperion Theater & Bar",
-- "The Lyric Hyperion") to the canonical club so organizer-mode shows converge to one row.
--
-- Idempotent: NOT EXISTS-guarded INSERTs (clubs by unique name, sources by club+scraper_key,
-- aliases by normalized name+city+state); no-ops where rows already exist. On a fresh DB the
-- scraper-created venue clubs are materialized here so eventbrite venue/organizer resolution lands
-- on these rows. Generated from prod state.


INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'The Upstairs Comedy Club Los Angeles', '1415 S Los Angeles St Ste C, Los Angeles, CA 90015, USA', 'https://www.theupstairsla.com/', 'Los Angeles', 'CA', '90015', 'US', 'club', 'ChIJMRaHpyDHwoARfxdlrCdXjDQ', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Upstairs Comedy Club Los Angeles');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Lyric Hyperion Theater & Cafe', '2106 Hyperion Ave, Los Angeles, CA 90027, USA', 'http://www.lyrichyperion.com/', 'Los Angeles', 'CA', '90027', 'US', 'club', 'ChIJK5t5CDXHwoARYkpSBd-2ZsE', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Lyric Hyperion Theater & Cafe');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'The Pack Theater', '1615 N Vermont Ave, Los Angeles, CA 90027, USA', 'http://www.packtheater.com/', 'Los Angeles', 'CA', '90027', 'US', 'club', 'ChIJEV0PuzO_woAR8t5H8l1Wyds', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Pack Theater');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Zebra Room Comedy', '5176 Santa Monica Blvd Ste 102, Los Angeles, CA 90029, USA', 'https://zebraroomcomedy.com/', 'Los Angeles', 'CA', '90029', 'US', 'club', 'ChIJ24qcKKm5woAR4ueR1OHBOpY', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Zebra Room Comedy');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'The Hollywood Comedy', '5871 Melrose Ave, Los Angeles, CA 90038, USA', 'http://www.thehollywoodcomedy.com/', 'Los Angeles', 'CA', '90038', 'US', 'club', 'ChIJxQflhz-5woARzD5VXPerrNM', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Hollywood Comedy');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'The Nitecap', '2200 W Burbank Blvd B, Burbank, CA 91506, USA', 'http://nitecap.la/', 'Burbank', 'CA', '91506', 'US', 'club', 'ChIJG4khZNKVwoARa4E23Wug6jk', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Nitecap');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'The FanaticSalon Theater | Culver City Comedy Club', '3815 Sawtelle Blvd, Los Angeles, CA 90066, USA', 'https://fanaticsalon.com/', 'Los Angeles', 'CA', '90066', 'US', 'club', 'ChIJFWFhOke6woARHLNAHNz53Uo', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The FanaticSalon Theater | Culver City Comedy Club');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'JEST Improv', '2750 E Main St Ste B2, Ventura, CA 93003, USA', 'http://www.jestimprov.com/', 'Ventura', 'CA', '93003', 'US', 'club', 'ChIJVUtOzJNN6IARBRU84_KygZ0', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'JEST Improv');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'The Welcome Room', '419 E Main St, Ventura, CA 93001, USA', 'https://www.thewelcomeroom.org/', 'Ventura', 'CA', '93001', 'US', 'club', 'ChIJN1vev1mt6YARQ03ODEEz_rQ', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Welcome Room');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Astronaut City', '1037 South Baldwin Avenue, Arcadia, CA', '', 'Arcadia', 'CA', '91007', 'US', 'club', 'ChIJB3p0G2jbwoAR_3xyps4XW2Y', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Astronaut City');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'The Rock Gallery Comedy Club', '333 N Palm Canyon Dr Unit 117', '', 'Palm Springs', 'CA', '92262', 'US', 'club', 'ChIJp2BV0xAb24AREVDImlDmMjQ', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Rock Gallery Comedy Club');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'The Hideaway Cafe & Lounge', '3660 Mission Inn Ave', '', 'Riverside', 'CA', '92501', 'US', 'club', 'ChIJG_zP_O-x3IARnwICOKUbCEI', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Hideaway Cafe & Lounge');

INSERT INTO clubs (name, address, website, city, state, zip_code, country, club_type, google_place_id, visible, status)
SELECT 'Best Comedy Club Near Me Theater', '7456 Melrose Ave', '', 'Los Angeles', 'CA', '90046', 'US', 'club', 'ChIJYQLAJGe_woARKwXbMB3AkLM', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Best Comedy Club Near Me Theater');



INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'tixr'::"ScrapingPlatform", 'tixr', 'https://www.theupstairsla.com/', NULL, NULL, NULL, 0, TRUE, '{"onboarded_via":"discover-comedy-venues 90012 (2026-06-17); group id 2391 captured via Playwright network capture; Tixr detail-page enrichment is DataDome/capsolver-blocked, so use the group-events API fallback","tixr_group_id":"2391","tixr_source_type":"group_events_api","datadome_dependent":false,"tixr_group_events_api_fallback":true}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Upstairs Comedy Club Los Angeles'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'tixr');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/58553675543', '58553675543', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Lyric Hyperion Theater & Cafe'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/51046842993', '51046842993', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Pack Theater'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/34302056277', '34302056277', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Zebra Room Comedy'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/29424734351', '29424734351', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Hollywood Comedy'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'tixr'::"ScrapingPlatform", 'tixr', 'https://nitecap.la/', NULL, NULL, NULL, 0, TRUE, '{"onboarded_via":"discover 90012 2026-06-17; group id 1357 via Playwright; Tixr detail pages DataDome-blocked","tixr_group_id":"1357","tixr_source_type":"group_events_api","datadome_dependent":false,"tixr_group_events_api_fallback":true}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Nitecap'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'tixr');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'tribe_events'::"ScrapingPlatform", 'the_events_calendar', 'https://fanaticsalon.com/wp-json/tribe/events/v1/events', NULL, NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The FanaticSalon Theater | Culver City Comedy Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'wix_events'::"ScrapingPlatform", 'wix_events', 'https://www.jestimprov.com', NULL, 'comp-mmzf8mp0', NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'JEST Improv'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'wix_events');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'json_ld', 'https://www.thewelcomeroom.org/events', NULL, NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Welcome Room'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'json_ld');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com', '296920705', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Astronaut City'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com', '289233853', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Rock Gallery Comedy Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com', '297895208', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Hideaway Cafe & Lounge'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, wix_event_id, seatengine_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com', '296478506', NULL, NULL, 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Best Comedy Club Near Me Theater'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');



INSERT INTO club_aliases (club_id, alias_name, normalized_alias_name, city, state, normalized_city, normalized_state, source, verified, created_at, updated_at)
SELECT c.id, 'Lyric Hyperion Theater & Bar', 'lyric hyperion theater and bar', 'Los Angeles', 'CA', 'los angeles', 'ca', 'discover_90012_consolidation', TRUE, now(), now()
FROM clubs c WHERE c.name = 'Lyric Hyperion Theater & Cafe'
  AND NOT EXISTS (SELECT 1 FROM club_aliases a WHERE a.normalized_alias_name = 'lyric hyperion theater and bar' AND a.normalized_city = 'los angeles' AND a.normalized_state = 'ca');

INSERT INTO club_aliases (club_id, alias_name, normalized_alias_name, city, state, normalized_city, normalized_state, source, verified, created_at, updated_at)
SELECT c.id, 'The Lyric Hyperion', 'the lyric hyperion', 'Los Angeles', 'CA', 'los angeles', 'ca', 'discover_90012_consolidation', TRUE, now(), now()
FROM clubs c WHERE c.name = 'Lyric Hyperion Theater & Cafe'
  AND NOT EXISTS (SELECT 1 FROM club_aliases a WHERE a.normalized_alias_name = 'the lyric hyperion' AND a.normalized_city = 'los angeles' AND a.normalized_state = 'ca');
