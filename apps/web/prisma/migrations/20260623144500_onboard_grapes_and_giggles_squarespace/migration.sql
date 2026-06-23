-- TASK-3190: Onboard Grapes & Giggles (San Carlos, CA), discovered via the
-- discover-comedy-venues skill near 94101/94102.
--
-- The venue's own site is a Squarespace site whose /shows page is an
-- events-stacked collection (id 63eabf17cace5b59ae68d0a7). Direct
-- GetItemsByMonth checks on 2026-06-23 returned dated Grapes & Giggles comedy
-- shows for June/July 2026, including "Grapes & Giggles in San Carlos @
-- Domenico". The existing generic `squarespace` scraper transformed the
-- current three-month window into 2 shows in a dry in-memory check.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

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
    status
)
SELECT
    'Grapes & Giggles',
    '1697 Industrial Rd, San Carlos, CA 94070, USA',
    'https://www.grapesandgiggles.com/',
    'San Carlos',
    'CA',
    '94070',
    'America/Los_Angeles',
    'US',
    'club',
    'ChIJoW1YGkCjj4ARu3WNJUq3SXs',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1
    FROM clubs
    WHERE google_place_id = 'ChIJoW1YGkCjj4ARu3WNJUq3SXs'
       OR name = 'Grapes & Giggles'
);

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
SELECT
    c.id,
    'squarespace'::"ScrapingPlatform",
    'squarespace',
    'https://www.grapesandgiggles.com/api/open/GetItemsByMonth?collectionId=63eabf17cace5b59ae68d0a7',
    0,
    TRUE,
    jsonb_build_object(
        'collection_id', '63eabf17cace5b59ae68d0a7',
        'collection_path', '/shows',
        'onboarded_via', 'TASK-3190'
    ),
    now(),
    now()
FROM clubs c
WHERE c.google_place_id = 'ChIJoW1YGkCjj4ARu3WNJUq3SXs'
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'squarespace'::"ScrapingPlatform"
        AND s.priority = 0
  );
