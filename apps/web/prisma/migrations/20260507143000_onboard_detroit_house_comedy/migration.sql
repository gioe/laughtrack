-- Onboard Detroit House of Comedy (TASK-2000).
-- Live backend discovery on 2026-05-07:
--   Page: https://detroit.houseofcomedy.net/upcoming-comedy-shows/
--   Backend: WordPress admin-ajax action get_comedy_shows
--   Ticketing: local /events/ links returned in the AJAX HTML response

WITH chain_row AS (
    INSERT INTO chains (
        name,
        slug,
        website
    )
    VALUES (
        'House of Comedy',
        'house-of-comedy',
        'https://houseofcomedy.net/'
    )
    ON CONFLICT (slug) DO UPDATE
    SET name = EXCLUDED.name,
        website = EXCLUDED.website
    RETURNING id
),
club_row AS (
    INSERT INTO clubs (
        name,
        address,
        website,
        visible,
        zip_code,
        phone_number,
        popularity,
        timezone,
        city,
        state,
        country,
        status,
        club_type,
        chain_id
    )
    SELECT
        'Detroit House of Comedy',
        '2301 Woodward Avenue, Detroit, MI 48201',
        'https://detroit.houseofcomedy.net/',
        TRUE,
        '48201',
        '313-312-4965',
        0,
        'America/Detroit',
        'Detroit',
        'MI',
        'US',
        'active',
        'club',
        id
    FROM chain_row
    ON CONFLICT (name) DO UPDATE
    SET address = EXCLUDED.address,
        website = EXCLUDED.website,
        visible = TRUE,
        zip_code = EXCLUDED.zip_code,
        phone_number = EXCLUDED.phone_number,
        timezone = EXCLUDED.timezone,
        city = EXCLUDED.city,
        state = EXCLUDED.state,
        country = EXCLUDED.country,
        status = 'active',
        club_type = 'club',
        chain_id = EXCLUDED.chain_id
    RETURNING id
)
INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    enabled,
    priority,
    metadata,
    created_at,
    updated_at
)
SELECT
    id,
    'custom',
    'house_of_comedy_detroit',
    'https://detroit.houseofcomedy.net/upcoming-comedy-shows/',
    TRUE,
    0,
    jsonb_build_object(
        'ajax_url', 'https://detroit.houseofcomedy.net/wp-admin/admin-ajax.php',
        'backend', 'WordPress admin-ajax action=get_comedy_shows',
        'ticketing', 'local House of Comedy /events/ links'
    ),
    NOW(),
    NOW()
FROM club_row
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
