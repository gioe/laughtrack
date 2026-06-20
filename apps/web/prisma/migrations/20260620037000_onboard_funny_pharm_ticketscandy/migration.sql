-- Onboard Funny Pharm Comedy Club via the new ticketscandy scraper — TASK-3024
--
-- Funny Pharm Comedy Club (1100 Chicago Ave, Goshen, IN) is a dedicated stand-up
-- club. Its WordPress /shows/ index links to per-comedian /shows/<slug>/ pages,
-- each of which links out to TicketsCandy event pages (ticketscandy.com/e/<slug>)
-- that carry schema.org Event JSON-LD. The new generic `ticketscandy` scraper
-- does the two-hop crawl (listing -> sub-pages via detail_link_prefix ->
-- TicketsCandy links), reuses the json_ld extractor, and corrects TicketsCandy's
-- mislabeled +00:00 offset + unreliable startDate time (preferring the title's
-- clock time) — localizing to the club's Eastern timezone.
--
-- Verified: real scrape returned 29 shows (all touring stand-up, Fri/Sat 7:30 PM
-- ET through Jan 2027), DST-correct.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Funny Pharm Comedy Club', '1100 Chicago Ave, Goshen, IN 46528', 'https://www.funnypharmcomedy.com', 'Goshen', 'IN', '46528', 'America/Indiana/Indianapolis', 'US', 'club', 'ChIJeXVkP93rFogRjK--gmr5Wmw', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Funny Pharm Comedy Club');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'ticketscandy', 'https://www.funnypharmcomedy.com/shows/', 0, TRUE,
  '{"detail_link_prefix": "/shows/"}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Funny Pharm Comedy Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'ticketscandy');
