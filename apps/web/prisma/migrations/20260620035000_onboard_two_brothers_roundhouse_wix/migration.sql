-- Onboard Two Brothers Roundhouse via wix_events + comedy_filter — TASK-2975
--
-- Two Brothers Roundhouse (205 N Broadway, Aurora, IL) is a mixed-use brewpub /
-- music venue whose Wix site (twobrothersbrewing.com) runs the Wix Events app.
-- Its calendar is mostly live music / trivia; the comedy programming is the
-- recurring "Still Not Friday - Comedy" series. The generic wix_events scraper
-- reads the paginated-events API (no compId needed — it returns all events) and
-- the comedy_filter metadata flag keeps only comedy-keyword titles.
--
-- Verified: real scrape returned 5 shows — 4x "Still Not Friday - Comedy" (the
-- target series) plus 1 false positive ("Pig Roast Celebrating Father's Day!",
-- matched on the "roast" keyword in is_comedy_event). The food-"roast" false
-- positive is tracked as a separate follow-up to harden the shared helper; it is
-- a single annual event and does not block onboarding the comedy series.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Two Brothers Roundhouse', '205 N Broadway, Aurora, IL 60505', 'https://www.twobrothersbrewing.com/restaurants/roundhouse', 'Aurora', 'IL', '60505', 'America/Chicago', 'US', 'club', 'ChIJWaXPhrz6DogRcGSBf_CNXRQ', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Two Brothers Roundhouse');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'wix_events'::"ScrapingPlatform", 'wix_events', 'https://www.twobrothersbrewing.com', 0, TRUE,
  '{"comedy_filter": true, "note": "TASK-2975 mixed-use brewpub; Still Not Friday comedy series. Known false positive: Pig Roast (roast keyword)."}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Two Brothers Roundhouse'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'wix_events');
