-- TASK-2868/2869/2871/2872/2876/2880/2890: Onboard Eventbrite-organizer comedy
-- venues discovered via the discover-comedy-venues skill (objective #2, ZIP 44622).
-- Each adds an anchor club + an `eventbrite` scraping source pointing at the
-- organizer's /o/ feed. Producer-brand organizers that produce at varying
-- venues are hidden synthetic proxies (visible=false) — their shows surface
-- under auto-created per-venue clubs; fixed venues are visible. Idempotent
-- (NOT EXISTS guards) so it no-ops where rows already exist (prod) and
-- reproduces state on fresh databases.


-- Snowflake Comedy (Eventbrite organizer 54965674123, hidden proxy)
INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Snowflake Comedy', '#1111, Cleveland, OH 44109, USA', 'https://www.snowflakecomedy.com/', 'Cleveland', 'OH', 'America/New_York', 'US', 'club', 'ChIJWwtj2DnvMIgRjH4fLlE9m54', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Snowflake Comedy');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/snowflake-comedy-club-54965674123', '54965674123', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Snowflake Comedy'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');


-- Henceforth Comedy (Formerly Secret Society Comedy) (Eventbrite organizer 25799034879, hidden proxy)
INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Henceforth Comedy (Formerly Secret Society Comedy)', '2190 W 37th St, Cleveland, OH 44113, USA', 'http://henceforthcomedy.com/', 'Cleveland', 'OH', 'America/New_York', 'US', 'club', 'ChIJ6a-nFCAjnK0R7HObv-_Jw6Y', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Henceforth Comedy (Formerly Secret Society Comedy)');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/25799034879', '25799034879', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Henceforth Comedy (Formerly Secret Society Comedy)'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');


-- Puff Puff Laugh Comedy Show (Eventbrite organizer 88694293243, hidden proxy)
INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Puff Puff Laugh Comedy Show', '1547 St Clair Ave NE, Cleveland, OH 44114, USA', 'https://puffpufflaugh.co/', 'Cleveland', 'OH', 'America/New_York', 'US', 'club', 'ChIJsxsQDtP7MIgRXo3OlSifmY0', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Puff Puff Laugh Comedy Show');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/puff-puff-laugh-comedy-show-88694293243', '88694293243', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Puff Puff Laugh Comedy Show'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');


-- Atomic Comedy Co. (Eventbrite organizer 113362373471)
INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Atomic Comedy Co.', '133 W Pike St, Canonsburg, PA 15317, USA', 'http://atomiccomedyco.com/', 'Canonsburg', 'PA', 'America/New_York', 'US', 'club', 'ChIJ3YsxNY5oiYURl6La5c9tEkk', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Atomic Comedy Co.');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/atomic-comedy-co-113362373471', '113362373471', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Atomic Comedy Co.'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');


-- The Rock Comedy Show Live (Eventbrite organizer 38700126763, hidden proxy)
INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Rock Comedy Show Live', '700 River Ave #335, Pittsburgh, PA 15212, USA', 'http://www.rockcomedyshow.com/', 'Pittsburgh', 'PA', 'America/New_York', 'US', 'club', 'ChIJT2oC0NXzNIgRVtpqMk32dCE', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Rock Comedy Show Live');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/roxamore-head-quarters-38700126763', '38700126763', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Rock Comedy Show Live'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');


-- Pagliacci's Comedy Club (Eventbrite organizer 68051880803)
INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Pagliacci''s Comedy Club', 'downstairs @ Manor Grill, 200 Main St, Irwin, PA 15642, USA', 'https://pagcomclub.com/', 'Irwin', 'PA', 'America/New_York', 'US', 'club', 'ChIJDz_cdnvbNIgRHLeEk3FRQ2I', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Pagliacci''s Comedy Club');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/brothers-grinn-productions-68051880803', '68051880803', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Pagliacci''s Comedy Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');


-- The Brothers Lounge (Eventbrite organizer 1332576191)
INSERT INTO clubs (name, address, website, city, state, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Brothers Lounge', '11609 Detroit Ave, Cleveland, OH 44102, USA', 'http://brotherslounge.com/', 'Cleveland', 'OH', 'America/New_York', 'US', 'club', 'ChIJKeH2f_LxMIgRbxzpeE5tiao', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Brothers Lounge');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/1332576191', '1332576191', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Brothers Lounge'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
