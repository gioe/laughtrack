-- Onboard Comedy Uncorked (a winery stand-up series) via the multi-date
-- `ticketspice` scraper - TASK-3254.
--
-- Comedy Uncorked (comedyuncorked.com) runs recurring stand-up shows at two
-- East-Bay wineries, each its own fixed venue, each selling through a single
-- TicketSpice (Webconnex) form that lists MULTIPLE upcoming dates:
--   * Retzlaff Vineyards, Livermore  -> comedy.ticketspice.com/2026-comedy-uncorked-retzlaff-vineyards
--   * Hannah Nicole Vineyards, Brentwood -> comedy.ticketspice.com/2026-comedy-uncorked-hannah-nicole-vineyards
--
-- MULTI-DATE: one form sells several show dates. appSettings.eventStart in the
-- window.__BOOTSTRAP__ names only the FIRST date; the full set lives in the
-- formData ticketBlock's date-selection `categories` (e.g. "June 27" / "July 18"
-- / "August 22", each with its own priced levels). The extended `ticketspice`
-- scraper (scraper_key='ticketspice', platform='custom') parses those categories
-- and emits ONE Show per upcoming date (show_page_url = the form URL), reusing
-- the wall-clock show time derived from eventStart localized to the form
-- timeZone. Single-date forms (The Stage at Burke / TASK-3207) still work via the
-- eventStart fallback.
--
-- source_url is each winery's TicketSpice form URL (the scraper fetches it).
-- visible=TRUE: both are real fixed venues.
--
-- Idempotent: re-running reuses each club (matched by google_place_id when set,
-- else name+city+state) and the existing ticketspice scraping_sources row.

-- 1) Retzlaff Vineyards (Livermore) ---------------------------------------- --
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Comedy Uncorked at Retzlaff Vineyards',
    '1356 S Livermore Ave, Livermore, CA 94550, USA',
    'https://comedyuncorked.com/livermore/',
    'Livermore', 'CA', '94550', 'America/Los_Angeles', 'US', 'club',
    'ChIJG2w9d4nnj4ARx6UleAIB2JY', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJG2w9d4nnj4ARx6UleAIB2JY'
       OR (lower(name) = lower('Comedy Uncorked at Retzlaff Vineyards')
           AND lower(city) = lower('Livermore') AND state = 'CA')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ticketspice',
    'https://comedy.ticketspice.com/2026-comedy-uncorked-retzlaff-vineyards',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJG2w9d4nnj4ARx6UleAIB2JY'
       OR (lower(c.name) = lower('Comedy Uncorked at Retzlaff Vineyards')
           AND lower(c.city) = lower('Livermore') AND c.state = 'CA'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'ticketspice'
  );

-- 2) Hannah Nicole Vineyards (Brentwood) ----------------------------------- --
-- No confirmed google_place_id at onboarding; idempotency keys on name+city+state.
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, visible, status
)
SELECT
    'Comedy Uncorked at Hannah Nicole Vineyards',
    '6700 Balfour Rd, Brentwood, CA 94513, USA',
    'https://comedyuncorked.com/brentwood/',
    'Brentwood', 'CA', '94513', 'America/Los_Angeles', 'US', 'club',
    TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE lower(name) = lower('Comedy Uncorked at Hannah Nicole Vineyards')
      AND lower(city) = lower('Brentwood') AND state = 'CA'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ticketspice',
    'https://comedy.ticketspice.com/2026-comedy-uncorked-hannah-nicole-vineyards',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE lower(c.name) = lower('Comedy Uncorked at Hannah Nicole Vineyards')
  AND lower(c.city) = lower('Brentwood') AND c.state = 'CA'
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'ticketspice'
  );
