-- TASK-3588: onboard verified first-party sources from the ComedyTickets
-- dedicated-club candidate set.
--
-- ComedyTickets is used only as a discovery signal. These rows were verified
-- against the venues' own sites and smoke-tested with existing scraper code:
--   * St. Louis Funny Bone: standup_media scraper, 113 future shows.
--   * Hyena's Comedy Nightclub Fort Worth: Prekindle JSON-LD, 90 future shows.
--
-- Duplicate guard: do not insert a club when either the canonical name already
-- exists or another row has the same normalized street-number/street-name key.

WITH candidates AS (
    SELECT *
    FROM (
        VALUES
            (
                'St. Louis Funny Bone',
                '614 W Port Plaza Dr, St. Louis, MO 63146',
                'https://stlouisfunnybone.com',
                '63146',
                '(314) 469-6692',
                'America/Chicago',
                'St. Louis',
                'MO',
                'custom',
                'standup_media',
                'https://stlouisfunnybone.com/events',
                '{"standup_media_location_id":"718bd264-309b-4fa0-a6fa-0b93455f88d0","standup_media_dbname":"stlouis_prod"}'::jsonb
            ),
            (
                'Hyena''s Comedy Nightclub Fort Worth',
                '425 Commerce Street, Fort Worth, TX 76102',
                'https://hyenascomedynightclub.com/fort-worth',
                '76102',
                '',
                'America/Chicago',
                'Fort Worth',
                'TX',
                'custom',
                'json_ld',
                'https://www.prekindle.com/events/hyenasfortworth',
                '{}'::jsonb
            )
    ) AS v(
        name,
        address,
        website,
        zip_code,
        phone_number,
        timezone,
        city,
        state,
        platform,
        scraper_key,
        source_url,
        metadata
    )
),
normalized_candidates AS (
    SELECT
        c.*,
        lower(regexp_replace(split_part(c.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) AS street_key
    FROM candidates c
),
inserted_clubs AS (
    INSERT INTO clubs (
        name,
        address,
        website,
        zip_code,
        phone_number,
        popularity,
        timezone,
        city,
        state,
        country,
        visible,
        status,
        club_type
    )
    SELECT
        nc.name,
        nc.address,
        nc.website,
        nc.zip_code,
        nc.phone_number,
        0,
        nc.timezone,
        nc.city,
        nc.state,
        'US',
        TRUE,
        'active',
        'club'
    FROM normalized_candidates nc
    WHERE NOT EXISTS (
        SELECT 1
        FROM clubs existing
        WHERE existing.name = nc.name
           OR lower(regexp_replace(split_part(existing.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) = nc.street_key
    )
    ON CONFLICT (name) DO NOTHING
    RETURNING id, name
),
preexisting_target_clubs AS (
    SELECT
        existing.id AS club_id,
        nc.name
    FROM normalized_candidates nc
    JOIN clubs existing
      ON existing.name = nc.name
      OR lower(regexp_replace(split_part(existing.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) = nc.street_key
),
target_clubs AS (
    SELECT
        COALESCE(ic.id, ptc.club_id) AS club_id,
        nc.platform,
        nc.scraper_key,
        nc.source_url,
        nc.metadata
    FROM normalized_candidates nc
    LEFT JOIN inserted_clubs ic ON ic.name = nc.name
    LEFT JOIN preexisting_target_clubs ptc ON ptc.name = nc.name
    WHERE COALESCE(ic.id, ptc.club_id) IS NOT NULL
)
INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    tc.club_id,
    tc.platform::"ScrapingPlatform",
    tc.scraper_key,
    tc.source_url,
    0,
    TRUE,
    tc.metadata
FROM target_clubs tc
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources ss
    WHERE ss.club_id = tc.club_id
      AND ss.enabled = TRUE
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET
    scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = EXCLUDED.metadata,
    updated_at = NOW()
WHERE scraping_sources.enabled = FALSE;
