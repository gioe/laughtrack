-- Onboard House of Comedy British Columbia (TASK-2001).
-- Live backend discovery on 2026-05-07:
--   Requested page: https://bc.houseofcomedy.net/shows-tickets/ returns Webflow Not Found.
--   Page used: https://bc.houseofcomedy.net/
--   Backend: Webflow CMS-rendered event cards on the homepage.
--   Ticketing: Tixr links in the card hrefs (groups/comicstripbc/events/*).

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
        'House of Comedy British Columbia',
        '530 Columbia Street, New Westminster, BC V3L 1B1',
        'https://bc.houseofcomedy.net/',
        TRUE,
        'V3L 1B1',
        '604-522-4500',
        0,
        'America/Vancouver',
        'New Westminster',
        'BC',
        'CA',
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
    'house_of_comedy_bc',
    'https://bc.houseofcomedy.net/',
    TRUE,
    0,
    jsonb_build_object(
        'backend', 'Webflow homepage event cards',
        'ticketing', 'Tixr groups/comicstripbc event links',
        'requested_url_status', 'https://bc.houseofcomedy.net/shows-tickets/ renders Webflow Not Found'
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
