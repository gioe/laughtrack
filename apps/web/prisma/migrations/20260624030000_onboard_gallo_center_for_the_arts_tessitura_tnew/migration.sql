-- Onboard Gallo Center for the Arts (Modesto, CA) via the generic tessitura_tnew scraper - TASK-3238.
--
-- The Gallo Center is a mixed-use performing-arts center whose box office runs on
-- Tessitura TNEW (tickets.galloarts.org loads production.tnew-assets.com and POSTs
-- /api/products/productionseasons). Its program spans ~30 genres (Broadway,
-- classical, opera, ballet, concerts, etc.); Comedy is one of them.
--
-- This wires to the generic `tessitura_tnew` scraper against the TNEW listing page
-- https://tickets.galloarts.org/events?view=list. Because the venue is mixed-use,
-- metadata.keyword_ids isolates comedy SERVER-SIDE: the TNEW EventGenres page maps
-- the "Comedy" genre to keyword id 78 (events?view=list&kid=78), and the
-- production-seasons API honors keywordIds=78 to return only comedy productions.
--
-- NOTE (verified 2026-06-24 against the live TNEW production-seasons API):
-- keywordIds="" returns 96 productions / 154 performances across all genres;
-- keywordIds=78 returns 8 productions / 10 comedy performances -- Marlon Wayans,
-- Lily Tomlin, Henry Cho, Peter Antoniou, Bored Teachers Comedy Tour, Drew Lynch,
-- One Man Star Wars Trilogy, Terry Fator -- and drops all non-comedy programming.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Gallo Center for the Arts',
    '1000 I St, Modesto, CA 95354, USA',
    'https://www.galloarts.org/',
    'Modesto', 'CA', '95354', 'America/Los_Angeles', 'US', 'club',
    'ChIJxUSiYY1TkIARyoqJVsMY_N4', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJxUSiYY1TkIARyoqJVsMY_N4'
       OR name = 'Gallo Center for the Arts'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'tessitura_tnew',
    'https://tickets.galloarts.org/events?view=list',
    TRUE,
    0,
    jsonb_build_object(
        'events_url', 'https://tickets.galloarts.org/events?view=list',
        'api_url', 'https://tickets.galloarts.org/api/products/productionseasons',
        'keyword_ids', '78'
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJxUSiYY1TkIARyoqJVsMY_N4' OR c.name = 'Gallo Center for the Arts')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'tessitura_tnew'
  );
