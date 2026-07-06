-- TASK-3607: onboard Olsen Run Comedy Club (Shopify).
--
-- Eugene OR's stand-up club sells shows as Shopify products at
-- https://olsenrun.com/collections/shows. The shopify scraper's Format A
-- variant-date parser was broadened in this task to read Olsen Run's variant
-- titles ("FRIDAY - JULY 10th 2026 / 6PM - EARLY SHOW"); smoke-tested 2026-07-06
-- -> 110 future shows. Verified/deferred in TASK-3592.
--
-- Duplicate guard: skip when the canonical name already exists or another row
-- shares the same normalized street key. Source guard: only insert when the
-- club has no other enabled source.

WITH candidates AS (
    SELECT *
    FROM (
        VALUES
            (
                'Olsen Run Comedy Club',
                '44 E 7th Avenue, Eugene, OR 97401',
                'https://olsenrun.com',
                '97401', '', 'America/Los_Angeles', 'Eugene', 'OR',
                'shopify', 'shopify', 'https://olsenrun.com/collections/shows'
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
