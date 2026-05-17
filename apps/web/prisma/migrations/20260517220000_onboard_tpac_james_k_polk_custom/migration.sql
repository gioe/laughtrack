-- Onboard James K. Polk Theater / TPAC (club 2571) from temporary
-- tour_dates discovery to the official TPAC comedy category endpoint.
--
-- Verification on 2026-05-17:
--   * TPAC serves over HTTPS at https://www.tpac.org.
--   * The official multicategory endpoint filters to Comedy (category=5) and
--     James K. Polk Theater (venue=4):
--     https://www.tpac.org/multicategory/category_json/0?category=5&venue=4&team=0&exclude=&per_page=6&came_from_page=event-list-page
--   * Detail pages expose stable title, date, time, venue, ticket URL, and
--     description fields consumed by the tpac_james_k_polk custom scraper.

DO $$
DECLARE
    matching_clubs integer;
BEGIN
    SELECT COUNT(*)
    INTO matching_clubs
    FROM clubs
    WHERE id = 2571
      AND name = 'James K. Polk Theater'
      AND city = 'Nashville'
      AND state = 'TN'
      AND visible = TRUE
      AND status = 'active';

    IF matching_clubs <> 1 THEN
        RAISE EXCEPTION 'Cannot onboard James K. Polk Theater: expected exactly one matching club row, found %', matching_clubs;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM scraping_sources
        WHERE id = 1579
          AND club_id = 2571
          AND platform = 'tour_dates'::"ScrapingPlatform"
          AND scraper_key = 'tour_dates'
          AND source_url = 'tour_dates'
          AND enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Cannot onboard James K. Polk Theater: expected tour_dates source 1579 is missing or changed';
    END IF;
END $$;

UPDATE clubs
SET website = 'https://www.tpac.org',
    address = 'Nashville, TN',
    country = 'US',
    timezone = 'America/Chicago'
WHERE id = 2571
  AND name = 'James K. Polk Theater'
  AND city = 'Nashville'
  AND state = 'TN'
  AND visible = TRUE
  AND status = 'active';

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'tour_date_onboarding_replaced', jsonb_build_object(
            'verified_at', '2026-05-17',
            'replacement_platform', 'custom',
            'replacement_scraper_key', 'tpac_james_k_polk',
            'replacement_source_url', 'https://www.tpac.org/multicategory/category_json/0?category=5&venue=4&team=0&exclude=&per_page=6&came_from_page=event-list-page',
            'rationale', 'Temporary tour_dates source replaced after verified TPAC category endpoint produced Polk Theater comedy events.'
        )
    ),
    updated_at = NOW()
WHERE id = 1579
  AND club_id = 2571
  AND platform = 'tour_dates'::"ScrapingPlatform"
  AND scraper_key = 'tour_dates';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata,
    created_at,
    updated_at
)
VALUES (
    2571,
    'custom'::"ScrapingPlatform",
    'tpac_james_k_polk',
    'https://www.tpac.org/multicategory/category_json/0?category=5&venue=4&team=0&exclude=&per_page=6&came_from_page=event-list-page',
    0,
    TRUE,
    jsonb_build_object(
        'tour_date_onboarding', jsonb_build_object(
            'verified_at', '2026-05-17',
            'official_site', 'https://www.tpac.org',
            'official_category_endpoint', 'https://www.tpac.org/multicategory/category_json/0?category=5&venue=4&team=0&exclude=&per_page=6&came_from_page=event-list-page',
            'category_id', 5,
            'venue_id', 4,
            'sample_events', jsonb_build_array(
                'Kevin Langue',
                'JK LIVE!',
                'Please Don''t Destroy',
                'Leslie Jones',
                'Nurse Blake'
            )
        )
    ),
    NOW(),
    NOW()
)
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    metadata = scraping_sources.metadata || EXCLUDED.metadata,
    updated_at = NOW();

DO $$
BEGIN
    IF to_regclass('public.club_aliases') IS NOT NULL THEN
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
                2571,
                'James K. Polk Theater',
                'james k polk theater',
                'Nashville',
                'TN',
                'nashville',
                'tn',
                '20260517220000: TPAC custom onboarding',
                TRUE
            ),
            (
                2571,
                'TPAC Polk Theater',
                'tpac polk theater',
                'Nashville',
                'TN',
                'nashville',
                'tn',
                '20260517220000: TPAC custom onboarding',
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
    END IF;
END $$;
