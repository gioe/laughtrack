-- Onboard medium-likelihood comedy venues discovered via discover-comedy-venues
-- near ZIP 02101 - TASK-3152 (batch 4 of 45, venues 31-40).
--
-- Of venues 31-40, 2 qualify; 8 dropped (see task notes):
--   - Marigold Theater (Easthampton): music-only calendar, 0 comedy.
--   - Lakeport Opera House (Laconia): etix, music/tribute only, 0 comedy.
--   - The Chicken Box (Nantucket): music-only + SeeTickets (no scraper).
--   - Infinity Music Hall (Hartford): ~1 comedy date among music; AXS scraper has
--     no comedy isolation and the venue's own site is Cloudflare-blocked.
--   - Playhouse on Park (West Hartford): real "Comedy Nights" series BUT ticketed
--     only via Tix.com (no scraper) and no JSON-LD on its own site — platform gap.
--   - Biddeford City Theater: community theater, 1 occasional comedy booking.
--   - Maine House of Comedy (Portland): closed / invite-only, no public calendar.
--   - Blue Portland Maine: music-focused, 0 comedy.
--
-- 31. Colonial Theatre Laconia (609 Main Street, Laconia, NH 03246) — Spectacle
--     Live historic theater on Etix (venue 17051) booking recurring touring stand-up
--     (Bob Marley, Lucas Zelnick, Juston McKinney) among mostly music/theater, so the
--     source opts into comedy isolation via metadata.comedy_filter. NOTE: etix is
--     DataDome-blocked from non-residential IPs, so a local scrape returns 0; the
--     venue id + comedy presence were confirmed via the venue's own ticket links and
--     the row scrapes on the residential-proxy nightly GHA run.
--
-- 32. Nantucket Dreamland (17 South Water Street, Nantucket, MA 02554) — runs a
--     dedicated "Dreamland Comedy" series + the Nantucket Comedy Festival, published
--     under a comedy-only WordPress taxonomy archive (/event-type/live-comedy) with no
--     JSON-LD and no events REST endpoint. Onboarded via a new venue-specific HTML
--     scraper (scraper_key 'dreamland') added in this task's scraper commit; the
--     archive is already comedy-only so no comedy_filter is needed. Verified
--     2026-06-22: a real scrape persisted 7 shows for the venue.

-- ---- Colonial Theatre Laconia (Etix, comedy_filter) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Colonial Theatre Laconia', '609 Main Street', 'https://coloniallaconia.com/',
    'Laconia', 'NH', '03246', 'America/New_York', 'US', 'club',
    'ChIJF-TI3EE0s0wR7s8_vZ8Q-w8', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJF-TI3EE0s0wR7s8_vZ8Q-w8'
       OR name = 'Colonial Theatre Laconia'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'etix'::"ScrapingPlatform",
    'etix',
    'https://www.etix.com/ticket/v/17051',
    TRUE,
    0,
    jsonb_build_object('comedy_filter', true),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJF-TI3EE0s0wR7s8_vZ8Q-w8' OR c.name = 'Colonial Theatre Laconia')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'etix'
  );

-- ---- Nantucket Dreamland (dreamland HTML scraper, archive is comedy-only) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Nantucket Dreamland', '17 South Water Street', 'http://www.nantucketdreamland.org/',
    'Nantucket', 'MA', '02554', 'America/New_York', 'US', 'club',
    'ChIJBaczHuDc-okRqOTqE1JB-RA', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJBaczHuDc-okRqOTqE1JB-RA'
       OR name = 'Nantucket Dreamland'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'dreamland',
    'https://www.nantucketdreamland.org/event-type/live-comedy',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJBaczHuDc-okRqOTqE1JB-RA' OR c.name = 'Nantucket Dreamland')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'dreamland'
  );
