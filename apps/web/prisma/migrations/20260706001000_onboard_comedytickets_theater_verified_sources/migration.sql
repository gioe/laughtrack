-- TASK-3589: onboard verified first-party sources from the ComedyTickets
-- theater/mixed-venue candidate set.
--
-- ComedyTickets is used only as a discovery signal. The enabled row below was
-- verified against the venue's own site and smoke-tested with existing scraper
-- code:
--   * Fallout Theater: Eventbrite single-venue mode, 172 future shows.
--
-- Duplicate guard: do not insert a club when either the canonical name already
-- exists or another row has the same normalized street-number/street-name key.

WITH candidates AS (
    SELECT *
    FROM (
        VALUES
            (
                'Fallout Theater',
                '616 Lavaca St, Austin, TX 78701',
                'https://falloutcomedy.com',
                '78701',
                '',
                'America/Chicago',
                'Austin',
                'TX',
                'eventbrite',
                'eventbrite',
                'https://www.eventbrite.com',
                '16738257328',
                '{"exclude_classes":true}'::jsonb
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
        eventbrite_id,
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
        nc.eventbrite_id,
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
    eventbrite_id,
    priority,
    enabled,
    metadata
)
SELECT
    tc.club_id,
    tc.platform::"ScrapingPlatform",
    tc.scraper_key,
    tc.source_url,
    tc.eventbrite_id,
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
    eventbrite_id = EXCLUDED.eventbrite_id,
    enabled = TRUE,
    metadata = EXCLUDED.metadata,
    updated_at = NOW()
WHERE scraping_sources.enabled = FALSE;
