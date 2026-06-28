-- Onboard The Port Comedy Club (Baltimore, MD) — TASK-3485.
--
-- The Port Comedy Club sells through the SeeTickets/Eventim US whitelabel
-- storefront. The storefront is Cloudflare-protected and client-rendered; the
-- generic `seetickets_whitelabel` scraper uses a multi-step Playwright browser
-- path to clear Cloudflare and page through the whitelabel AJAX event list by
-- profile + affiliate key.
--
-- Fixed venue -> visible=true.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club. Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Port Comedy Club',
       '813 S Broadway, Baltimore, MD 21231',
       'https://portcomedy.com/',
       'Baltimore', 'MD', '21231',
       'America/New_York', 'US', 'club',
       'ChIJX_Pp9AwDyIkReTsKNN7MEG4',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'The Port Comedy Club'
     OR google_place_id = 'ChIJX_Pp9AwDyIkReTsKNN7MEG4'
);

-- 2. The SeeTickets/Eventim whitelabel scraping source. platform 'custom'
-- because seetickets_whitelabel is resolved by scraper_key rather than a
-- ScrapingPlatform enum member.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'seetickets_whitelabel',
       'https://wl.eventim.us/?afflky=ThePortComedyClub',
       0, true,
       jsonb_build_object(
         'profile_id', '15127815',
         'whitelabel_key', 'ThePortComedyClub',
         'affiliate_key', 'ThePortComedyClub',
         'max_months', 12,
         'page_size', 15
       )
FROM clubs c
WHERE (c.name = 'The Port Comedy Club' OR c.google_place_id = 'ChIJX_Pp9AwDyIkReTsKNN7MEG4')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'seetickets_whitelabel'
  );
