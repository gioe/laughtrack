-- Onboard Fox Theatre (Redwood City, CA) via the generic showare scraper - TASK-3220.
--
-- The Fox Theatre is a multi-purpose historic theatre (Latin concerts, tribute
-- bands, recitals, immersive "experiences") that also hosts touring stand-up
-- comedy (e.g. Brincos Dieras "El Desmadre Continua Tour" / "Elite Comedy Fest").
-- It tickets through accesso ShoWare at foxrwc.showare.com, so this wires to the
-- generic `showare` scraper (source_url = the ShoWare default.asp). Because the
-- host is multi-purpose, metadata.include_title_patterns scopes the feed to comedy
-- so the concert/recital season does not surface.
--
-- The ShoWare performance-list `Event` field (which the scraper filters on) carries
-- the act name, not always the word "comedy" (e.g. the current comedy show's Event
-- is "Brincos Dieras" while its PerformanceName is "Elite Comedy Fest"). So the
-- include set combines generic comedy keywords with the known touring comedian's
-- name. As future comedy acts are listed they can be added to the pattern set
-- (Clayton Club precedent, TASK-3192). A 0-show scrape when no comedy is currently
-- on the calendar is expected, not a failure, for a comedy-filtered mixed-use source.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Fox Theatre Redwood City', '2215 Broadway, Redwood City, CA 94063, USA',
    'https://foxrwc.com/',
    'Redwood City', 'CA', '94063', 'America/Los_Angeles', 'US', 'club',
    'ChIJ5_eDzFKij4ARR8mqZagHhM8', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJ5_eDzFKij4ARR8mqZagHhM8'
       OR name = 'Fox Theatre Redwood City'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'showare',
    'https://foxrwc.showare.com/default.asp',
    TRUE,
    0,
    jsonb_build_object(
        'include_title_patterns',
        jsonb_build_array(
            'comedy', 'comedian', 'stand.?up', 'improv', 'sketch',
            'open mic', 'roast', 'brincos dieras'
        )
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ5_eDzFKij4ARR8mqZagHhM8' OR c.name = 'Fox Theatre Redwood City')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'showare'
  );
