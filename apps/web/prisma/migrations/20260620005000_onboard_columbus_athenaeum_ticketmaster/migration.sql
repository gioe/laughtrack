-- Onboard The Columbus Athenaeum (Columbus, OH) — TASK-2906
--
-- The Columbus Athenaeum (32 N 4th St; columbusmeetings.com) is a historic
-- (1896) downtown event venue — primarily private/corporate events, but its
-- Athenaeum Theatre periodically hosts ticketed national stand-up tours
-- (e.g. David Cross, Esparza) sold via Ticketmaster. Handled by the existing
-- generic `ticketmaster_comedy` scraper (Discovery API, Comedy classification
-- filter), scoped to the venue's Discovery venueId KovZpZA17ItA. Fixed venue →
-- visible=true.
--
-- NOTE: at onboarding time the venue had 0 currently-listed Ticketmaster events
-- of any kind (verified via Discovery API + a real scrape: HTTP 200, 0 comedy
-- events). The wiring is correct; the nightly scraper will surface comedy shows
-- as they are announced. Onboarded now (per operator decision) so future tours
-- are caught without re-discovery.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Columbus Athenaeum', '32 N 4th St, Columbus, OH 43215', 'https://www.columbusmeetings.com', 'Columbus', 'OH', '43215', 'America/New_York', 'US', 'club', 'ChIJtVD_ZjKPOIgRnFAFNN0LY68', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Columbus Athenaeum');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, ticketmaster_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'ticketmaster'::"ScrapingPlatform", 'ticketmaster_comedy', 'https://www.ticketmaster.com', 'KovZpZA17ItA', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Columbus Athenaeum'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'ticketmaster_comedy');
