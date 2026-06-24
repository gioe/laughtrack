-- Onboard Lucky Penny Community Arts Center (Napa, CA) via the generic ovationtix scraper - TASK-3224.
--
-- Lucky Penny is a 99-seat mixed-use community theater (musicals, plays, the
-- occasional stand-up comedy night) that tickets through OvationTix
-- (client id 36167; the venue's site embeds ci.ovationtix.com/36167/... buy
-- links). This wires to the generic `ovationtix` scraper via the server-rendered
-- calendar https://web.ovationtix.com/trs/cal/36167 (ovationtix_id=36167).
-- Because the venue is mixed-use, metadata.comedy_filter isolates comedy
-- (keyword + known-comedian heuristic) from the plays/musicals.
--
-- NOTE (verified 2026-06-23 against the live OvationTix API for client 36167):
-- the series view lists 8 upcoming productions. 7 are plays/musicals -- "Freaky
-- Friday: The Musical", "It's a Wonderful Life: A Live Radio Play", "Revenge of
-- the Rebobs!", "Come From Away", "Matilda", "Our Town", "Honky Tonk Angels" --
-- and 1 is stand-up: "Comedy Night with Johnny Steele and Friends" (2026-06-27).
-- The comedy_filter keyword regex matches only the "Comedy Night" production and
-- drops the 7 non-comedy ones, so only the stand-up show persists.
--
-- TASK-3224 is the canonical onboard for this physical venue; sibling TASK-3225
-- ("Lucky Penny Productions") is the same venue/website and dedupes against this
-- club (clubs.name is UNIQUE; this row also guards on google_place_id).

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Lucky Penny Community Arts Center',
    '1758 Industrial Way #208, Napa, CA 94558, USA',
    'https://www.luckypennynapa.com/',
    'Napa', 'CA', '94558', 'America/Los_Angeles', 'US', 'club',
    'ChIJDQpHR-cGhYARA5qFayJqJFo', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJDQpHR-cGhYARA5qFayJqJFo'
       OR name = 'Lucky Penny Community Arts Center'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, ovationtix_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'ovationtix'::"ScrapingPlatform",
    'ovationtix',
    'https://web.ovationtix.com/trs/cal/36167',
    '36167',
    TRUE,
    0,
    jsonb_build_object('comedy_filter', true),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJDQpHR-cGhYARA5qFayJqJFo' OR c.name = 'Lucky Penny Community Arts Center')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'ovationtix'
  );
