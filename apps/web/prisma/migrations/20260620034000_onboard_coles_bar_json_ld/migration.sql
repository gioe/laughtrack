-- Onboard Cole's Bar via json_ld + comedy_filter — TASK-2964
--
-- Cole's Bar (2338 N Milwaukee Ave, Chicago, IL) is a mixed-use live-music
-- venue / neighborhood bar / comedy room. Its Opendate-powered storefront
-- (colesbarchicago.com) lists every upcoming show under /shows/<slug>, and each
-- detail page embeds schema.org MusicEvent JSON-LD (name/startDate/offers).
-- The generic json_ld scraper's detail_fetch mode harvests the /shows/ anchor
-- URLs from the homepage and extracts each MusicEvent. Because the calendar is
-- ~85% live music, the new comedy_filter metadata flag (TASK-2964) keeps only
-- events whose title/description match a comedy keyword — here the weekly
-- "Comedy Open Mic" (est. 2009).
--
-- Verified: real scrape returned 28 comedy shows (all "Comedy Open Mic",
-- recurring weekly through Dec 2026); all live-music shows excluded.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Cole''s Bar', '2338 N Milwaukee Ave, Chicago, IL 60647', 'https://colesbarchicago.com/', 'Chicago', 'IL', '60647', 'America/Chicago', 'US', 'club', 'ChIJQ_ORYGLND4gRxGOgGm82S10', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Cole''s Bar');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'json_ld', 'https://colesbarchicago.com/', 0, TRUE,
  '{"detail_fetch": {"enabled": true, "url_path_prefix": "/shows/"}, "comedy_filter": true}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Cole''s Bar'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'json_ld');
