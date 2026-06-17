-- Onboard CAPA — Columbus Association for the Performing Arts (Columbus, OH) — TASK-2924
--
-- CAPA operates a cluster of downtown Columbus venues (Ohio Theatre, Palace
-- Theatre, Southern Theatre, Lincoln Theatre, and the Davidson Theatre at the
-- Riffe Center) and presents touring stand-up across them (Whitney Cummings,
-- Gary Gulman, Jo Koy, Daniel Sloss, Ilana Glazer, Dusty Slay, …). Surfaced
-- during TASK-2882 (Slapstik onboarding): Slapstik's own Tribe calendar is
-- empty and its real shows live on capa.com.
--
-- Modeled as ONE venue-operator club (not per-venue): every comedy production
-- carries its specific theatre in the scraped Show.room, so a single operator
-- club captures the full CAPA comedy slate without fragmenting the venue list.
--
-- Datasource: CAPA's Tessitura→WordPress integration. The Tessitura box office
-- (tickets.capa.com) is bot/Queue-It protected and not directly scrapable, but
-- capa.com exposes the productions over the WP REST API
-- (/wp-json/wp/v2/tessi_production) with a comedy-filterable `genre` taxonomy
-- (Comedy = 73 productions). Handled by the NEW generic `tessitura` scraper.
-- platform='custom' because Tessitura has no dedicated ScrapingPlatform enum
-- value. Verified: 18 future comedy shows scraped live from www.capa.com.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status)
SELECT 'CAPA (Columbus)', '55 East State Street, Columbus, OH 43215', 'https://www.capa.com', 'Columbus', 'OH', '43215', 'America/New_York', 'US', 'club', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'CAPA (Columbus)');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'tessitura', 'https://www.capa.com', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'CAPA (Columbus)'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'tessitura');
