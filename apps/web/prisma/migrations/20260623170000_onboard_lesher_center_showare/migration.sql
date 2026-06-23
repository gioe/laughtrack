-- Onboard Lesher Center for the Arts (Walnut Creek, CA) via the generic showare scraper - TASK-3189.
--
-- The Lesher Center is a multi-arts center (Center Rep theatre season, concerts,
-- dance, recitals) that also hosts a "Comedy and Improv at LCA" series (Comedy
-- Night, The Real Irish Comedy Fest, Whose Live Anyway?, etc.). It tickets through
-- accesso ShoWare at lesherartscenter.showare.com, so this wires to the generic
-- `showare` scraper (source_url = the ShoWare default.asp). Because the host is
-- multi-purpose, metadata.include_title_patterns scopes the feed to comedy so the
-- theatre/concert/dance season does not surface.
--
-- NOTE (2026-06-23): the verifying scrape could NOT be run from the onboarding
-- sandbox — lesherartscenter.showare.com is unreachable from that environment
-- (DNS could-not-resolve on the scraper's curl egress, ECONNREFUSED on WebFetch),
-- so a local scrape returns 0 for network reasons, not config. The host is live
-- publicly (its ShoWare ticket pages are reachable elsewhere). Verification is
-- deferred to the next nightly GHA scrape (different egress); the
-- include_title_patterns should be tuned from the real ShoWare title set once
-- that run reveals it.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Lesher Center for the Arts', '1601 Civic Dr, Walnut Creek, CA 94596, USA',
    'https://www.lesherartscenter.org/',
    'Walnut Creek', 'CA', '94596', 'America/Los_Angeles', 'US', 'club',
    'ChIJUdDSPJVhhYARYSoFskv1gAg', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJUdDSPJVhhYARYSoFskv1gAg'
       OR name = 'Lesher Center for the Arts'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'showare',
    'https://lesherartscenter.showare.com/default.asp',
    TRUE,
    0,
    jsonb_build_object(
        'include_title_patterns',
        jsonb_build_array('comedy', 'improv', 'comedian', 'stand.?up', 'sketch', 'open mic', 'whose live', 'roast')
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJUdDSPJVhhYARYSoFskv1gAg' OR c.name = 'Lesher Center for the Arts')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'showare'
  );
