-- Onboard City Winery Boston from tour_dates-only discovery.
--
-- Investigation on 2026-05-14 found club 2423 "City Winery Boston" as an
-- active, visible tour_dates-only stub with no Boston duplicate. City Winery's
-- Shopify listing/API supports Boston with:
--   https://awsapi.citywinery.com/events?location=Boston&top=16&skip=0&genre=Comedy
--
-- The scraper_key remains custom because City Winery has no typed platform
-- enum; per-location API config lives in scraping_sources.metadata.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs
        WHERE id = 2423
          AND name = 'City Winery Boston'
          AND city = 'Boston'
          AND state = 'MA'
          AND visible = TRUE
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard City Winery Boston: club 2423 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2423
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2423
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2423
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2423
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2423
    ) THEN
        RAISE EXCEPTION 'Cannot onboard City Winery Boston: dependent rows already exist';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://citywinery.com/pages/events/boston',
    address = '80 Beverly Street',
    zip_code = '02114',
    timezone = 'America/New_York'
WHERE id = 2423
  AND name = 'City Winery Boston';

UPDATE scraping_sources
SET priority = 1,
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'city_winery_preserved_as_fallback', TRUE,
        'fallback_after_source', 'city_winery'
    ),
    updated_at = NOW()
WHERE club_id = 2423
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
    2423,
    'custom',
    'city_winery',
    'https://citywinery.com/pages/events/boston',
    TRUE,
    0,
    jsonb_build_object(
        'api_url', 'https://awsapi.citywinery.com/events',
        'location', 'Boston',
        'genre', 'Comedy',
        'listing_url', 'https://citywinery.com/pages/genre/boston-comedy',
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
        2423,
        'City Winery Boston',
        'city winery boston',
        'Boston',
        'MA',
        'boston',
        'ma',
        'City Winery Boston onboarding migration',
        TRUE
    ),
    (
        2423,
        'City Winery - Boston',
        'city winery - boston',
        'Boston',
        'MA',
        'boston',
        'ma',
        'City Winery Boston onboarding migration',
        TRUE
    ),
    (
        2423,
        'City Winery',
        'city winery',
        'Boston',
        'MA',
        'boston',
        'ma',
        'City Winery Boston onboarding migration',
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
