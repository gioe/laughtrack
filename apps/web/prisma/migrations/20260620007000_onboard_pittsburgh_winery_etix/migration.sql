-- Onboard The Original Pittsburgh Winery (Pittsburgh, PA) — TASK-2940
--
-- Independent music+comedy venue (NOT the City Winery chain — City Winery
-- Pittsburgh is club 8720, onboarded separately with a genre=Comedy filter).
-- The Original Pittsburgh Winery (2809 Penn Ave; pittsburghwinery.com) sells all
-- show tickets via Etix venue 31604
-- (etix.com/ticket/v/31604/the-original-pittsburgh-winery) -> the existing
-- generic `etix` scraper, which extracts venue_id 31604 from source_url.
--
-- Mixed programming: mostly live music with recurring stand-up (Kevin Nealon,
-- Greg Warren, Jimbo Jackson, Danny Golden). The etix scraper has no genre
-- filter, so it ingests the full venue calendar (music + comedy); per operator
-- decision (TASK-2940) the non-comedy music acts are pruned manually. Fixed
-- venue -> visible=TRUE.
--
-- NOTE: at onboarding time a local scrape returned 0 shows because etix.com
-- is DataDome-protected and the local capsolver could not solve the challenge.
-- The wiring is correct; N>0 verification is deferred to the post-merge GHA
-- nightly (residential-proxy allowlisted for etix). If the nightly is also
-- blocked, the follow-up is a pittsburghwinery.com venue-own-site fallback in
-- the etix scraper (mirroring the Funny Bone Rockhouse-Partners fallback).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Original Pittsburgh Winery', '2809 Penn Ave, Pittsburgh, PA 15222', 'https://www.pittsburghwinery.com', 'Pittsburgh', 'PA', '15222', 'America/New_York', 'US', 'club', 'ChIJqUxpEwDzNIgRyygsFtlyjAU', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Original Pittsburgh Winery');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'etix'::"ScrapingPlatform", 'etix', 'https://www.etix.com/ticket/v/31604/the-original-pittsburgh-winery', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Original Pittsburgh Winery'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'etix');
