-- Onboard Raue Center + The Vixen via Etix (comedy-filtered) — TASK-2976 / TASK-2977
--
-- Both are mixed-use Etix venues that host comedy alongside concerts/plays, now
-- onboardable thanks to the etix comedy filter (TASK-3010). Each source sets
-- metadata.comedy_filter=true:
--   - Raue Center For The Arts (Crystal Lake, IL) — etix venue_id 16722; comedy
--     is touring comedians (Paula Poundstone, etc.) caught by the known-comedian
--     heuristic.
--   - The Vixen (McHenry, IL) — etix venue_id 28278; mostly live music, comedy is
--     a recurring "FREE Stand Up Comedy Every Wednesday" caught by the keyword.
--
-- Onboarded HIDDEN (visible=false): Etix is DataDome-protected, so the scrape
-- can't be verified on a residential IP — populates on the GHA nightly. Flip to
-- visible after confirming comedy-only output (tracked on TASK-2976 / TASK-2977).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Raue Center For The Arts', '26 N Williams St, Crystal Lake, IL 60014', 'http://www.rauecenter.org/', 'Crystal Lake', 'IL', '60014', 'America/Chicago', 'US', 'club', 'ChIJA-KLJ6JyD4gRoRBP3cFCXNk', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Raue Center For The Arts');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'etix'::"ScrapingPlatform", 'etix', 'https://www.etix.com/ticket/v/16722/raue-center-for-the-arts', 0, TRUE, '{"comedy_filter": true}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Raue Center For The Arts'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'etix');

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Vixen', '1208 N Green St, McHenry, IL 60050', 'https://vixenmchenry.com/', 'McHenry', 'IL', '60050', 'America/Chicago', 'US', 'club', 'ChIJ1bOqjOBwD4gRT2Z-KdfeTn8', FALSE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Vixen');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'etix'::"ScrapingPlatform", 'etix', 'https://www.etix.com/ticket/v/28278/the-vixen', 0, TRUE, '{"comedy_filter": true}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Vixen'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'etix');
