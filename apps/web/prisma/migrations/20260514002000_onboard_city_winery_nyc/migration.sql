-- Onboard City Winery NYC from tour_dates-only discovery (TASK-2187).
--
-- Investigation on 2026-05-14 found canonical club 2420
-- "City Winery - New York City" and duplicate club 3020 "City Winery".
-- Both were active tour_dates-only stubs with no dependent show/tag/email/
-- production-company rows. City Winery's Shopify listing calls:
--   https://awsapi.citywinery.com/events?location=New%20York%20City&top=16&skip=0&genre=Comedy
--
-- The scraper_key remains custom because City Winery has no typed platform
-- enum; per-location API config lives in scraping_sources.metadata.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs
        WHERE id = 2420
          AND name = 'City Winery - New York City'
          AND city = 'New York'
          AND state = 'NY'
          AND visible = TRUE
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard City Winery NYC: canonical club 2420 is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM clubs
        WHERE id = 3020
          AND name = 'City Winery'
          AND city = 'New York'
          AND state = 'NY'
          AND visible = TRUE
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot handle duplicate City Winery club: duplicate club 3020 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 3020
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 3020
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 3020
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 3020
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 3020
    ) THEN
        RAISE EXCEPTION 'Cannot hide duplicate City Winery club 3020: dependent rows exist';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://citywinery.com/pages/events/new-york-city',
    address = '25 11th Ave',
    zip_code = '10011',
    timezone = 'America/New_York'
WHERE id = 2420
  AND name = 'City Winery - New York City';

UPDATE scraping_sources
SET priority = 1,
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_2187_preserved_as_fallback', TRUE,
        'fallback_after_source', 'city_winery'
    ),
    updated_at = NOW()
WHERE club_id = 2420
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates'
  AND priority = 0;

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
VALUES (
    2420,
    'custom',
    'city_winery',
    'https://citywinery.com/pages/events/new-york-city',
    TRUE,
    0,
    jsonb_build_object(
        'api_url', 'https://awsapi.citywinery.com/events',
        'location', 'New York City',
        'genre', 'Comedy',
        'listing_url', 'https://citywinery.com/pages/genre/new-york-city-comedy',
        'ticket_url_template', 'https://tickets.citywinery.com/event/{url}',
        'pagination', 'top=16; increment skip by 16 until total_events exhausted; 404 beyond end is expected'
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

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
VALUES
    (
        2420,
        'City Winery',
        'city winery',
        'New York',
        'NY',
        'new york',
        'ny',
        'TASK-2187 duplicate club 3020',
        TRUE
    ),
    (
        2420,
        'City Winery - New York City',
        'city winery - new york city',
        'New York',
        'NY',
        'new york',
        'ny',
        'TASK-2187 canonical venue name',
        TRUE
    )
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
DO UPDATE SET
    club_id = EXCLUDED.club_id,
    alias_name = EXCLUDED.alias_name,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    source = EXCLUDED.source,
    verified = TRUE,
    updated_at = NOW();

UPDATE clubs
SET name = 'City Winery (duplicate of club 2420)',
    visible = FALSE,
    status = 'closed',
    closed_at = NOW()
WHERE id = 3020
  AND name = 'City Winery'
  AND city = 'New York'
  AND state = 'NY'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_2187_disposition', 'duplicate_of_club_2420',
        'canonical_club_id', 2420,
        'canonical_scraper_key', 'city_winery',
        'disabled_reason', 'duplicate_tour_dates_stub',
        'verified_at', '2026-05-14'
    ),
    updated_at = NOW()
WHERE club_id = 3020
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';
