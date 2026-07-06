-- TASK-3606: onboard Ann Arbor Comedy Showcase (etix venue 515).
--
-- aacomedy.com names Etix as its official ticketing partner (etix venue 515).
-- The etix scraper is proven in production for the Funny Bone chain; the venue
-- could not be smoke-tested locally because etix.com is DataDome-walled from
-- this IP (capsolver rejects the etix URL) -- an environment artifact, not a
-- scraper defect. The GHA nightly (residential/different WAF behavior) is the
-- authoritative smoke test and is verified post-merge. Verified/deferred in
-- TASK-3592.
--
-- Duplicate guard: skip when the canonical name already exists or another row
-- shares the same normalized street key. Source guard: only insert when the
-- club has no other enabled source.

WITH candidates AS (
    SELECT *
    FROM (
        VALUES
            (
                'Ann Arbor Comedy Showcase',
                '212 S 4th Ave, Ann Arbor, MI 48104',
                'https://www.aacomedy.com',
                '48104', '', 'America/Detroit', 'Ann Arbor', 'MI',
                'etix', 'etix', 'https://www.etix.com/ticket/v/515/ann-arbor-comedy-showcase'
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
