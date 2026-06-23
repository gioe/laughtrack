-- Onboard Safe Words Comedy Show (San Francisco, CA) via the generic json_ld scraper - TASK-3177.
--
-- Safe Words is San Francisco's longest-running queer comedy showcase, a monthly
-- stand-up series at SF Eagle (398 12th St). Its own site (teamwonderdave.com/safe-words)
-- sells tickets through Humanitix, exposing the upcoming shows on the collections
-- page https://collections.humanitix.com/safe-words-queer-comedy-showcase, whose
-- HTML embeds JSON-LD Event blocks inside an ItemList. The generic json_ld scraper
-- recurses that ItemList and extracts each show -- no new scraper code needed.
--
-- NOTE (verified 2026-06-23): a real scrape extracts and persists 2 upcoming shows.
-- This onboard depends on the TASK-3177 enhancement fix that falls back to the event
-- URL for a ticket purchase_url when an offer (the leading Humanitix AggregateOffer)
-- carries no url of its own; without it, validation dropped both shows.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Safe Words Comedy Show', '398 12th St, San Francisco, CA 94103, USA',
    'https://www.teamwonderdave.com/safe-words',
    'San Francisco', 'CA', '94103', 'America/Los_Angeles', 'US', 'club',
    'ChIJB6hOWSZ_j4ARQ9l-SmvWQTs', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJB6hOWSZ_j4ARQ9l-SmvWQTs'
       OR name = 'Safe Words Comedy Show'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'json_ld',
    'https://collections.humanitix.com/safe-words-queer-comedy-showcase',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJB6hOWSZ_j4ARQ9l-SmvWQTs' OR c.name = 'Safe Words Comedy Show')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'json_ld'
  );
