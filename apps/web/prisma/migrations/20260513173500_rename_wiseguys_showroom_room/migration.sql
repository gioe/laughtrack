-- TASK-2173: Model "The Showroom" as room data for the Salt Lake City
-- Wiseguys venue instead of as the club name.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs c
        JOIN scraping_sources ss ON ss.club_id = c.id
        WHERE c.id = 390
          AND c.name = 'Wiseguys - The Showroom'
          AND LOWER(TRIM(c.city)) = 'salt lake city'
          AND LOWER(TRIM(c.state)) = 'ut'
          AND c.visible = TRUE
          AND c.status = 'active'
          AND c.chain_id = 10
          AND ss.id = 644
          AND ss.platform = 'seatengine'::"ScrapingPlatform"
          AND ss.scraper_key = 'seatengine'
          AND ss.source_url = 'https://www.wiseguyscomedy.com/utah/salt-lake-city/the-showroom'
          AND ss.seatengine_id = 361
          AND ss.enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot rename club 390: expected Wiseguys Showroom SeatEngine source is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2399
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2399
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2399
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2399
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2399
    ) THEN
        RAISE EXCEPTION 'Cannot close duplicate club 2399: dependent rows exist';
    END IF;
END $$;

UPDATE clubs
SET
    name = 'Wiseguys Comedy Club - Salt Lake City',
    website = 'https://www.wiseguyscomedy.com/utah/salt-lake-city'
WHERE id = 390
  AND name = 'Wiseguys - The Showroom'
  AND city = 'Salt Lake City'
  AND state = 'UT';

WITH alias_seed (
    club_id,
    alias_name,
    normalized_alias_name,
    city,
    state,
    normalized_city,
    normalized_state,
    source
) AS (
    VALUES
        (
            390,
            'Wiseguys - The Showroom',
            'wiseguys the showroom',
            'Salt Lake City',
            'UT',
            'salt lake city',
            'ut',
            'TASK-2173: former club 390 room-specific venue name'
        ),
        (
            390,
            'Wise Guys Conedy Club',
            'wise guys conedy club',
            'Salt Lake City',
            'UT',
            'salt lake city',
            'ut',
            'TASK-2173: duplicate tour_dates stub 2399'
        )
)
INSERT INTO club_aliases (
    club_id,
    alias_name,
    normalized_alias_name,
    city,
    state,
    normalized_city,
    normalized_state,
    source,
    verified
)
SELECT
    s.club_id,
    s.alias_name,
    s.normalized_alias_name,
    s.city,
    s.state,
    s.normalized_city,
    s.normalized_state,
    s.source,
    TRUE
FROM alias_seed AS s
JOIN clubs AS c
  ON c.id = s.club_id
 AND c.name = 'Wiseguys Comedy Club - Salt Lake City'
 AND LOWER(TRIM(c.city)) = s.normalized_city
 AND LOWER(TRIM(c.state)) = s.normalized_state
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
DO UPDATE SET
    club_id = EXCLUDED.club_id,
    alias_name = EXCLUDED.alias_name,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    source = EXCLUDED.source,
    verified = TRUE,
    updated_at = NOW();

UPDATE shows AS s
SET room = 'The Showroom'
WHERE s.club_id = 390
  AND (s.room IS NULL OR BTRIM(s.room) = '')
  AND NOT EXISTS (
      SELECT 1
      FROM shows existing
      WHERE existing.club_id = s.club_id
        AND existing.date = s.date
        AND existing.room = 'The Showroom'
  );

UPDATE clubs
SET
    name = 'Wise Guys Conedy Club (duplicate of club 390)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 2399
  AND name = 'Wise Guys Conedy Club'
  AND city = 'Salt Lake City'
  AND state = 'UT'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET
    enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_tour_date_onboarding_disposition', 'duplicate_of_club_390',
        'canonical_club_id', 390,
        'canonical_source_id', 644,
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-13'
    )
WHERE club_id = 2399
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
