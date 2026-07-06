-- TASK-3604: onboard New York Comedy Club - Stamford.
--
-- Stamford has its own dedicated first-party calendar at
-- https://stamford.newyorkcomedyclub.com/calendar (single-venue subdomain,
-- JSON-LD ComedyEvent). The new_york_comedy_club scraper's single-venue path
-- (added in this task) returns its shows directly; smoke-tested 2026-07-06 ->
-- 31 shows (28 future). Verified/deferred in TASK-3592.
--
-- Duplicate guard: skip when the canonical name already exists or another row
-- shares the same normalized street key. Source guard: only insert when the
-- club has no other enabled source.

WITH candidates AS (
    SELECT *
    FROM (
        VALUES
            (
                'New York Comedy Club - Stamford',
                '230 Tresser Blvd, Stamford, CT 06901',
                'https://stamford.newyorkcomedyclub.com',
                '06901', '', 'America/New_York', 'Stamford', 'CT',
                'custom', 'new_york_comedy_club', 'https://stamford.newyorkcomedyclub.com/calendar'
            )
    ) AS v(
        name, address, website, zip_code, phone_number, timezone, city, state,
        platform, scraper_key, source_url
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
        name, address, website, zip_code, phone_number, popularity,
        timezone, city, state, country, visible, status, club_type
    )
    SELECT
        nc.name, nc.address, nc.website, nc.zip_code, nc.phone_number, 0,
        nc.timezone, nc.city, nc.state, 'US', TRUE, 'active', 'club'
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
    SELECT existing.id AS club_id, nc.name
    FROM normalized_candidates nc
    JOIN clubs existing
      ON existing.name = nc.name
      OR lower(regexp_replace(split_part(existing.address, ',', 1), '[^a-zA-Z0-9]+', '', 'g')) = nc.street_key
),
target_clubs AS (
    SELECT
        COALESCE(ic.id, ptc.club_id) AS club_id,
        nc.platform, nc.scraper_key, nc.source_url
    FROM normalized_candidates nc
    LEFT JOIN inserted_clubs ic ON ic.name = nc.name
    LEFT JOIN preexisting_target_clubs ptc ON ptc.name = nc.name
    WHERE COALESCE(ic.id, ptc.club_id) IS NOT NULL
)
INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, priority, enabled, metadata
)
SELECT
    tc.club_id,
    tc.platform::"ScrapingPlatform",
    tc.scraper_key,
    tc.source_url,
    0,
    TRUE,
    '{}'::jsonb
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
