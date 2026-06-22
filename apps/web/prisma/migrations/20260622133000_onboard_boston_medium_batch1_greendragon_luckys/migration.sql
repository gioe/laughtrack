-- Onboard medium-likelihood Boston-cluster comedy venues discovered via
-- discover-comedy-venues near ZIP 02101 - TASK-3152 (batch 1 of 45, venues 1-10).
--
-- Of the first 10 medium-likelihood venues triaged, 2 qualify (real recurring
-- comedy calendar + scrapable datasource); 8 dropped (see task notes):
--   - Charles Playhouse: comedy runs under "Lil Chuck Boston" (already onboarded).
--   - CSz Boston / Riot Theater: resident improv companies at Rozzie Square Theater
--     (5 Basile St); ticketed shows surface under Rozzie (tracked separately).
--   - The Tam: weekly open mic exists but only renders via headless BentoBox CMS;
--     no static HTML / JSON-LD / ticketing funnel — not scrapable with our scrapers.
--   - Citizens House of Blues: Live Nation/Ticketmaster music hall, zero comedy.
--   - Slades Bar & Grill: music/DJ bar, no website, no comedy organizer/series.
--   - Midway Cafe: static-HTML live-music bar, no events page; comedy only on aggregators.
--   - Sanctuary Cultural Arts (Maynard): ShoWare, but only 1 one-off comedy show.
--
-- 1. The Green Dragon Tavern (11 Marshall St., Boston, MA 02108) — WordPress + The
--    Events Calendar. Weekly "Open Comedy Night" (Mondays). Wired via the generic
--    json_ld scraper against the comedy-only series page. Verified 2026-06-22:
--    a real scrape persisted 7 shows for club 10967.
--
-- 2. Lucky's Lounge (355 Congress Street, Boston, MA 02210) — Seaport lounge running
--    a recurring Monday standup series; tickets via the Eventbrite organizer
--    "Lucky's Lounge Comedy" (id 53821450233). Verified 2026-06-22: a real scrape
--    persisted 15 shows for club 10968.

-- ---- The Green Dragon Tavern (json_ld) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'The Green Dragon Tavern', '11 Marshall St.', 'http://www.greendragonboston.com/',
    'Boston', 'MA', '02108', 'America/New_York', 'US', 'club',
    'ChIJnZfW9YVw44kRp5FwX3GRHcg', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJnZfW9YVw44kRp5FwX3GRHcg'
       OR name = 'The Green Dragon Tavern'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://www.greendragonboston.com/series/open-comedy-night/',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJnZfW9YVw44kRp5FwX3GRHcg' OR c.name = 'The Green Dragon Tavern')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );

-- ---- Lucky's Lounge (Eventbrite) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Lucky''s Lounge', '355 Congress Street', 'http://luckyslounge.com/',
    'Boston', 'MA', '02210', 'America/New_York', 'US', 'club',
    'ChIJMU1-F4B644kRh4FgssOldKQ', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJMU1-F4B644kRh4FgssOldKQ'
       OR name = 'Lucky''s Lounge'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/luckys-lounge-comedy-53821450233',
    '53821450233',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJMU1-F4B644kRh4FgssOldKQ' OR c.name = 'Lucky''s Lounge')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
