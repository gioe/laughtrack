-- Onboard City Winery Chicago via the generic City Winery API scraper - TASK-2991
--
-- City Winery Chicago is a mixed music/comedy venue, but City Winery's API
-- supports server-side genre filtering:
--   https://awsapi.citywinery.com/events?location=Chicago&top=16&skip=0&genre=Comedy
--
-- Verified on 2026-06-19: the filtered API returned HTTP 200 with 23 comedy
-- events for Chicago, including Tee Sanders, Dustin Ross, Nephew Tommy,
-- Christian Johnson, and D.L. Hughley. The scraper_key remains custom because
-- City Winery has no typed platform enum; per-location API config lives in
-- scraping_sources.metadata.

INSERT INTO clubs (
    name,
    address,
    website,
    city,
    state,
    zip_code,
    timezone,
    country,
    club_type,
    google_place_id,
    visible,
    status,
    chain_id
)
SELECT
    'City Winery Chicago',
    '1200 W Randolph St, Chicago, IL 60607',
    'https://citywinery.com/pages/events/chicago',
    'Chicago',
    'IL',
    '60607',
    'America/Chicago',
    'US',
    'club',
    'ChIJ7ZBcatgsDogRVeUuWDAD0TM',
    TRUE,
    'active',
    16
WHERE NOT EXISTS (
    SELECT 1
    FROM clubs
    WHERE google_place_id = 'ChIJ7ZBcatgsDogRVeUuWDAD0TM'
       OR name = 'City Winery Chicago'
);

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
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'city_winery',
    'https://citywinery.com/pages/events/chicago',
    TRUE,
    0,
    jsonb_build_object(
        'api_url', 'https://awsapi.citywinery.com/events',
        'location', 'Chicago',
        'genre', 'Comedy',
        'listing_url', 'https://citywinery.com/pages/genre/chicago-comedy',
        'ticket_url_template', 'https://tickets.citywinery.com/event/{url}',
        'pagination', 'top=16; increment skip by 16 until total_events exhausted; 404 beyond end is expected'
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ7ZBcatgsDogRVeUuWDAD0TM' OR c.name = 'City Winery Chicago')
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.scraper_key = 'city_winery'
  );

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
    c.id,
    alias.alias_name,
    alias.normalized_alias_name,
    'Chicago',
    'IL',
    'chicago',
    'il',
    'City Winery Chicago onboarding migration',
    TRUE
FROM clubs c
CROSS JOIN (
    VALUES
        ('City Winery Chicago', 'city winery chicago'),
        ('City Winery - Chicago', 'city winery - chicago'),
        ('City Winery', 'city winery')
) AS alias(alias_name, normalized_alias_name)
WHERE (c.google_place_id = 'ChIJ7ZBcatgsDogRVeUuWDAD0TM' OR c.name = 'City Winery Chicago')
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
DO UPDATE SET
    club_id = EXCLUDED.club_id,
    alias_name = EXCLUDED.alias_name,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    source = EXCLUDED.source,
    verified = TRUE,
    updated_at = NOW();
