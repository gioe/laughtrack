-- Onboard The Underground Laugh Lounge via json_ld + comedy_filter — TASK-2979
--
-- The Underground Laugh Lounge (321 E Main St, Niles, MI) is a comedy club that
-- shares its WordPress site / event calendar with "The Study" bar. The Events
-- Calendar (Tribe) REST API is disabled (404), but every show emits schema.org
-- Event JSON-LD on both the /shows/ listing and each /shows/<slug> detail page.
-- The generic json_ld scraper's detail_fetch mode harvests the /shows/ anchor
-- URLs and extracts each Event; comedy_filter drops the co-listed non-comedy
-- bar programming (Acoustic Guitar Night, Trivia, Bingo, Tarot, piano).
--
-- Verified: real scrape returned 8 comedy shows (weekly comedy headliner
-- shows + Comedy Showcase + Free Comedy & Karaoke); all "The Study" non-comedy
-- events excluded by comedy_filter.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Underground Laugh Lounge', '321 E Main St, Niles, MI 49120', 'https://www.undergroundlaughlounge.com', 'Niles', 'MI', '49120', 'America/Detroit', 'US', 'club', 'ChIJeSTrgOHVFogRThccJA9glzU', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Underground Laugh Lounge');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'json_ld', 'https://undergroundlaughlounge.com/shows/', 0, TRUE,
  '{"detail_fetch": {"enabled": true, "url_path_prefix": "/shows/"}, "comedy_filter": true}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Underground Laugh Lounge'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'json_ld');
