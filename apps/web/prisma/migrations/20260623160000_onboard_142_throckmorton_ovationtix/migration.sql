-- Onboard 142 Throckmorton Theatre (Mill Valley, CA) via the generic ovationtix scraper - TASK-3187.
--
-- 142 Throckmorton is a multi-arts theater (comedy, music, plays, dance) that
-- tickets through OvationTix (client id 35161). It runs a weekly "Tuesday Night
-- Comedy" series plus touring comedians. This wires to the generic `ovationtix`
-- scraper (server-rendered calendar https://web.ovationtix.com/trs/cal/35161,
-- ovationtix_id=35161); because the venue is mixed-use, metadata.comedy_filter
-- isolates comedy (keyword + known-comedian heuristic) from the plays/concerts.
--
-- NOTE (verified 2026-06-23): a real scrape discovers 4 productions, the comedy
-- filter drops the 2 non-comedy ones, and 11 comedy shows persist
-- (Tuesday Night Comedy! + Don McMillan).

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    '142 Throckmorton Theatre', '142 Throckmorton Ave, Mill Valley, CA 94941, USA',
    'https://www.throckmortontheatre.org/',
    'Mill Valley', 'CA', '94941', 'America/Los_Angeles', 'US', 'club',
    'ChIJHxGWeG2QhYARcYmQlEBFg4w', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJHxGWeG2QhYARcYmQlEBFg4w'
       OR name = '142 Throckmorton Theatre'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, ovationtix_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'ovationtix'::"ScrapingPlatform",
    'ovationtix',
    'https://web.ovationtix.com/trs/cal/35161',
    '35161',
    TRUE,
    0,
    jsonb_build_object('comedy_filter', true),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJHxGWeG2QhYARcYmQlEBFg4w' OR c.name = '142 Throckmorton Theatre')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'ovationtix'
  );
