-- Onboard Side Splitters Comedy Theatre at The Grove (Wesley Chapel, FL).
--
-- This is a separate Side Splitters location from the Tampa club at
-- 12938 N Dale Mabry Hwy. The Grove page still uses OvationTix client 35579
-- (ci.ovationtix.com/35579), not the Tampa Punchup calendar.
--
-- Verification on 2026-06-28: the generic ovationtix scraper against
-- https://web.ovationtix.com/trs/cal/35579 returned 30 upcoming shows with
-- pricing sections.

WITH chain_row AS (
    INSERT INTO chains (
        name,
        slug,
        website
    )
    VALUES (
        'Side Splitters',
        'side-splitters',
        'https://sidesplitterscomedy.com'
    )
    ON CONFLICT (slug) DO UPDATE
    SET name = EXCLUDED.name,
        website = EXCLUDED.website
    RETURNING id
)
INSERT INTO clubs (
    name,
    address,
    website,
    city,
    state,
    zip_code,
    timezone,
    country,
    club_type,
    chain_id,
    visible,
    status
)
SELECT
    'Side Splitters Comedy Theatre at The Grove',
    '6333 Wesley Grove Blvd Theater #7, Wesley Chapel, FL 33544',
    'https://sidesplitterscomedy.com/locations/the-grove-at-wesley-chapel/',
    'Wesley Chapel',
    'FL',
    '33544',
    'America/New_York',
    'US',
    'club',
    (SELECT id FROM chain_row),
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1
    FROM clubs
    WHERE name = 'Side Splitters Comedy Theatre at The Grove'
       OR address = '6333 Wesley Grove Blvd Theater #7, Wesley Chapel, FL 33544'
       OR website = 'https://sidesplitterscomedy.com/locations/the-grove-at-wesley-chapel/'
);

UPDATE clubs
SET chain_id = (SELECT id FROM chains WHERE slug = 'side-splitters')
WHERE name = 'Side Splitters Comedy Theatre at The Grove'
   OR address = '6333 Wesley Grove Blvd Theater #7, Wesley Chapel, FL 33544'
   OR website = 'https://sidesplitterscomedy.com/locations/the-grove-at-wesley-chapel/';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    ovationtix_id,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
SELECT
    c.id,
    'ovationtix',
    'ovationtix',
    'https://web.ovationtix.com/trs/cal/35579',
    '35579',
    0,
    TRUE,
    jsonb_build_object(
        'migration_20260628131500',
        jsonb_build_object(
            'kind', 'side_splitters_grove_primary_calendar',
            'verification', 'Generic ovationtix scrape returned 30 upcoming shows on 2026-06-28.'
        )
    ),
    NOW(),
    NOW()
FROM clubs AS c
WHERE (
    c.name = 'Side Splitters Comedy Theatre at The Grove'
    OR c.address = '6333 Wesley Grove Blvd Theater #7, Wesley Chapel, FL 33544'
    OR c.website = 'https://sidesplitterscomedy.com/locations/the-grove-at-wesley-chapel/'
)
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources AS s
      WHERE s.club_id = c.id
        AND s.scraper_key = 'ovationtix'
        AND s.ovationtix_id = '35579'
  );
