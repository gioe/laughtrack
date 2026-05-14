-- Onboard City Winery Atlanta from tour_dates-only discovery.
--
-- Investigation on 2026-05-14 found club 2426 "City Winery Atlanta" as an
-- active, visible tour_dates-only stub with no Atlanta duplicate. City Winery's
-- Shopify listing/API supports Atlanta with:
--   https://awsapi.citywinery.com/events?location=Atlanta&top=16&skip=0&genre=Comedy
--
-- The scraper_key remains custom because City Winery has no typed platform
-- enum; per-location API config lives in scraping_sources.metadata.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clubs
        WHERE id = 2426
          AND name = 'City Winery Atlanta'
          AND city = 'Atlanta'
          AND state = 'GA'
          AND visible = TRUE
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard City Winery Atlanta: club 2426 is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM chains
        WHERE id = 16
          AND slug = 'city-winery'
          AND name = 'City Winery'
    ) THEN
        RAISE EXCEPTION 'Cannot onboard City Winery Atlanta: City Winery chain 16 is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1 FROM shows WHERE club_id = 2426
        UNION ALL
        SELECT 1 FROM tagged_clubs WHERE club_id = 2426
        UNION ALL
        SELECT 1 FROM email_subscriptions WHERE club_id = 2426
        UNION ALL
        SELECT 1 FROM processed_emails WHERE club_id = 2426
        UNION ALL
        SELECT 1 FROM production_company_venues WHERE club_id = 2426
    ) THEN
        RAISE EXCEPTION 'Cannot onboard City Winery Atlanta: dependent rows already exist';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://citywinery.com/pages/events/atlanta',
    address = '650 North Avenue NE',
    zip_code = '30308',
    timezone = 'America/New_York',
    chain_id = 16
WHERE id = 2426
  AND name = 'City Winery Atlanta';

UPDATE scraping_sources
SET priority = 1,
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'city_winery_preserved_as_fallback', TRUE,
        'fallback_after_source', 'city_winery'
    ),
    updated_at = NOW()
WHERE club_id = 2426
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
    2426,
    'custom',
    'city_winery',
    'https://citywinery.com/pages/events/atlanta',
    TRUE,
    0,
    jsonb_build_object(
        'api_url', 'https://awsapi.citywinery.com/events',
        'location', 'Atlanta',
        'genre', 'Comedy',
        'listing_url', 'https://citywinery.com/pages/genre/atlanta-comedy',
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
        2426,
        'City Winery Atlanta',
        'city winery atlanta',
        'Atlanta',
        'GA',
        'atlanta',
        'ga',
        'City Winery Atlanta onboarding migration',
        TRUE
    ),
    (
        2426,
        'City Winery - Atlanta',
        'city winery - atlanta',
        'Atlanta',
        'GA',
        'atlanta',
        'ga',
        'City Winery Atlanta onboarding migration',
        TRUE
    ),
    (
        2426,
        'City Winery',
        'city winery',
        'Atlanta',
        'GA',
        'atlanta',
        'ga',
        'City Winery Atlanta onboarding migration',
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
