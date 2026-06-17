-- Onboard Club Cafe (Pittsburgh, PA) — TASK-2930
--
-- Club Cafe (56 S 12th St, Pittsburgh PA 15203; clubcafelive.com) is a live-music
-- room that also hosts comedy (e.g. "WDVE Comedyfest Loaded Showcase"). Fixed
-- venue → visible=TRUE.
--
-- Datasource: the TicketWeb VENUE page
-- https://www.ticketweb.com/venue/club-cafe-pittsburgh-pa/23219 carries clean
-- JSON-LD MusicEvent/TheaterEvent blocks (name/startDate/url), handled by the
-- generic `json_ld` scraper. Club Cafe's own Squarespace /upcoming-shows page
-- embeds raw ticketweb links but NO structured data, so json_ld points at the
-- TicketWeb venue page instead.
--
-- The venue page is Cloudflare-protected and previously returned HTTP 530 to the
-- scraper (TASK-2930): the shared session sent a static Chrome-135 User-Agent
-- over a chrome124 curl_cffi TLS fingerprint, and Cloudflare flagged the
-- mismatch. Fixed in the same task by letting curl_cffi impersonation own the
-- UA/client-hint headers. platform='custom' (json_ld has no dedicated
-- ScrapingPlatform enum value). Verified: 20 upcoming shows scraped incl. comedy.
--
-- NOTE: prior rows from the TASK-2894 attempt were already deleted (the scrape
-- 530-blocked), so this is a fresh insert.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status, google_place_id)
SELECT 'Club Cafe', '56 South 12th Street, Pittsburgh, PA 15203', 'https://clubcafelive.com', 'Pittsburgh', 'PA', '15203', 'America/New_York', 'US', 'club', TRUE, 'active', 'ChIJufCTCULxNIgRf0ML_NvB4Kg'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Club Cafe' AND city = 'Pittsburgh');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'json_ld', 'https://www.ticketweb.com/venue/club-cafe-pittsburgh-pa/23219', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Club Cafe' AND c.city = 'Pittsburgh'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'json_ld');
