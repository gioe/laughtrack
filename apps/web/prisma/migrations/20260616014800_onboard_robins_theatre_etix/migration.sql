-- TASK-2887: Onboard Robins Theatre (Warren, OH), discovered via the
-- discover-comedy-venues skill (objective #2, ZIP 44622). A restored 1,400-seat
-- historic theatre that programs touring stand-up headliners year-round alongside
-- concerts and classic-film screenings (a mixed venue, like Pritchard Laughlin).
-- Tickets sell through Etix (venue id 6228) — scraped by the generic `etix`
-- scraper. Fixed venue → visible=true.
--
-- NOTE: Etix is DataDome-protected. Local scrapes from a residential IP get a
-- 403 interstitial (0 shows); the nightly GHA run uses the residential proxy that
-- already scrapes the other onboarded Etix venues (e.g. the Funny Bone clubs,
-- 200+ shows each), so a real-scrape N>0 is verified post-merge on the nightly,
-- not locally. The Etix venue id 6228 is confirmed real (sourced from
-- robinstheatre.com's own etix.com ticket links; returns 403 DataDome, not 404).
--
-- Idempotent (NOT EXISTS guards) so it no-ops where rows already exist (prod)
-- and reproduces state on fresh databases.


-- Robins Theatre (Etix)
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Robins Theatre', '160 E Market St, Warren, OH 44481, USA', 'https://robinstheatre.com', 'Warren', 'OH', '44481', 'America/New_York', 'US', 'club', 'ChIJFeUUOQdgMYgRoleN1TprRrU', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Robins Theatre');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'etix'::"ScrapingPlatform", 'etix', 'https://www.etix.com/ticket/v/6228/robins-theatre', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Robins Theatre'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'etix');
