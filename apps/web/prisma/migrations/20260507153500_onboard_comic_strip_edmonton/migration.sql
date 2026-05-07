-- Onboard The Comic Strip West Edmonton Mall (TASK-2002).
-- Live backend discovery on 2026-05-07:
--   Official venue page: https://wem.thecomicstrip.ca/
--   West Edmonton Mall directory redirects to: /directory/stores/the-comic-strip-wem
--   Backend: Webflow CMS-rendered event cards on the official homepage.
--   Ticketing: Tixr links in the card hrefs (groups/comicstripedmonton/events/*).
--   Scraper: custom Webflow-card extraction; direct Tixr detail fetches hit DataDome.

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
        'The Comic Strip West Edmonton Mall',
        '8882 170 Street NW, Unit 1646, Edmonton, AB T5T 4M2',
        'https://wem.thecomicstrip.ca/',
        TRUE,
        'T5T 4M2',
        '780-483-5999',
        0,
        'America/Edmonton',
        'Edmonton',
        'AB',
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
    'comic_strip_edmonton',
    'https://wem.thecomicstrip.ca/',
    TRUE,
    0,
    jsonb_build_object(
        'backend', 'Webflow homepage event cards',
        'ticketing', 'Tixr groups/comicstripedmonton event links',
        'scraper_path', 'custom Webflow-card extraction avoids DataDome-blocked Tixr detail pages',
        'calendar_url', 'https://www.pixlcalendar.com/comic-strip-edmonton',
        'mall_directory_url', 'https://www.wem.ca/directory/stores/the-comic-strip-wem'
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
