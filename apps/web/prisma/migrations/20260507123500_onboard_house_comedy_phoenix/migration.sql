-- Onboard Rick Bronson's House of Comedy Phoenix / High Street (TASK-1999).
-- Live backend discovery on 2026-05-07:
--   Page: https://az.houseofcomedy.net/upcoming-comedy-shows/
--   Backend: WordPress admin-ajax action get_comedy_shows
--   Ticketing: ShowClix links in the AJAX HTML response

WITH club_row AS (
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
        club_type
    )
    VALUES (
        'Rick Bronson''s House of Comedy Phoenix',
        '5350 E High St #105, Phoenix, AZ 85054',
        'https://az.houseofcomedy.net/',
        TRUE,
        '85054',
        '480-420-3553',
        0,
        'America/Phoenix',
        'Phoenix',
        'AZ',
        'US',
        'active',
        'club'
    )
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
        club_type = 'club'
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
    'house_of_comedy_phoenix',
    'https://az.houseofcomedy.net/upcoming-comedy-shows/',
    TRUE,
    0,
    jsonb_build_object(
        'ajax_url', 'https://az.houseofcomedy.net/wp-admin/admin-ajax.php',
        'backend', 'WordPress admin-ajax action=get_comedy_shows',
        'ticketing', 'ShowClix'
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
