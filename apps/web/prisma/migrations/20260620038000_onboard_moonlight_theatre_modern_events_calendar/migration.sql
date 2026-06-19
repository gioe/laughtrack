-- Onboard Moonlight Theatre via Modern Events Calendar - TASK-2999
--
-- Moonlight Theatre uses WordPress Modern Events Calendar. Its public
-- mec-events REST collection has a filterable Comedy category:
--   https://moonlighttheatre.com/wp-json/wp/v2/mec-events?mec_category=47
--
-- Verified on 2026-06-19:
--   - mec_category 47 is "Comedy" and has 101 rows.
--   - Rendered event detail pages include schema.org Event JSON-LD with
--     startDate, endDate, offers, and description.
--   - Live scraper verification parsed the first 60 comedy detail pages; latest
--     show was 2026-06-04, so the source is currently a valid empty calendar.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Moonlight Theatre', '7 S 2nd Ave, St. Charles, IL 60174', 'https://moonlighttheatre.com/', 'St. Charles', 'IL', '60174', 'America/Chicago', 'US', 'club', 'ChIJ-cDPg00DD4gRruZ2YX0CB-E', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1
    FROM clubs
    WHERE google_place_id = 'ChIJ-cDPg00DD4gRruZ2YX0CB-E'
       OR name = 'Moonlight Theatre'
);

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'modern_events_calendar',
    'https://moonlighttheatre.com/wp-json/wp/v2/mec-events?mec_category=47',
    0,
    TRUE,
    jsonb_build_object(
        'platform_note', 'WordPress Modern Events Calendar; mec_category=47 is Comedy',
        'listing_url', 'https://moonlighttheatre.com/event-category/comedy/',
        'force_js_rendering', TRUE,
        'per_page', 20,
        'max_pages', 3,
        'max_detail_pages', 60,
        'set_same_as_to_detail_url', TRUE
    ),
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJ-cDPg00DD4gRruZ2YX0CB-E' OR c.name = 'Moonlight Theatre')
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.scraper_key = 'modern_events_calendar'
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
    'St. Charles',
    'IL',
    'st charles',
    'il',
    'Moonlight Theatre onboarding migration',
    TRUE
FROM clubs c
CROSS JOIN (
    VALUES
        ('Moonlight Theatre', 'moonlight theatre'),
        ('Moonlight Theater', 'moonlight theater')
) AS alias(alias_name, normalized_alias_name)
WHERE (c.google_place_id = 'ChIJ-cDPg00DD4gRruZ2YX0CB-E' OR c.name = 'Moonlight Theatre')
ON CONFLICT (normalized_alias_name, normalized_city, normalized_state)
DO UPDATE SET
    club_id = EXCLUDED.club_id,
    alias_name = EXCLUDED.alias_name,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    source = EXCLUDED.source,
    verified = TRUE,
    updated_at = NOW();
