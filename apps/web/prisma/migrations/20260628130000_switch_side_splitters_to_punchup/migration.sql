-- Switch Side Splitters Comedy Club (Tampa, FL) from stale OvationTix to its
-- current Punchup-hosted calendar at sidesplitterscomedytampa.punchup.live.
--
-- Verification on 2026-06-28: the scraper HTTP stack fetched the Punchup page
-- and Punchup pagination returned 172 upcoming shows with Tixologi ticket IDs.

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
UPDATE clubs
SET chain_id = (SELECT id FROM chain_row)
WHERE name = 'Side Splitters Comedy Club';

UPDATE scraping_sources AS s
SET enabled = FALSE,
    metadata = COALESCE(s.metadata, '{}'::jsonb) || jsonb_build_object(
        'migration_20260628130000',
        jsonb_build_object(
            'kind', 'stale_ovationtix_replaced_by_punchup',
            'replacement_source_url', 'https://sidesplitterscomedytampa.punchup.live/',
            'rationale', 'Venue now publishes its current Tampa calendar on Punchup; keep the legacy OvationTix calendar disabled.'
        )
    ),
    updated_at = NOW()
FROM clubs AS c
WHERE c.id = s.club_id
  AND c.name = 'Side Splitters Comedy Club'
  AND s.platform = 'ovationtix';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
SELECT
    c.id,
    'custom',
    'side_splitters',
    'https://sidesplitterscomedytampa.punchup.live/',
    0,
    TRUE,
    jsonb_build_object(
        'migration_20260628130000',
        jsonb_build_object(
            'kind', 'punchup_primary_calendar',
            'verification', 'Live Punchup pagination returned 172 shows on 2026-06-28.'
        )
    ),
    NOW(),
    NOW()
FROM clubs AS c
WHERE c.name = 'Side Splitters Comedy Club'
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources AS existing
      WHERE existing.club_id = c.id
        AND existing.scraper_key = 'side_splitters'
  );

UPDATE scraping_sources AS s
SET platform = 'custom',
    scraper_key = 'side_splitters',
    source_url = 'https://sidesplitterscomedytampa.punchup.live/',
    priority = 0,
    enabled = TRUE,
    metadata = COALESCE(s.metadata, '{}'::jsonb) || jsonb_build_object(
        'migration_20260628130000',
        jsonb_build_object(
            'kind', 'punchup_primary_calendar',
            'verification', 'Live Punchup pagination returned 172 shows on 2026-06-28.'
        )
    ),
    updated_at = NOW()
FROM clubs AS c
WHERE c.id = s.club_id
  AND c.name = 'Side Splitters Comedy Club'
  AND s.scraper_key = 'side_splitters';

UPDATE clubs
SET website = 'https://sidesplitterscomedy.com',
    city = 'Tampa',
    state = 'FL',
    zip_code = '33618',
    timezone = 'America/New_York',
    visible = TRUE,
    status = 'active',
    chain_id = (SELECT id FROM chains WHERE slug = 'side-splitters')
WHERE name = 'Side Splitters Comedy Club';
