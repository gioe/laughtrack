-- Annotate Rose City Comedy's current Tixr source with the TASK-2011 audit.
-- The venue-owned page is fetchable and exposes Tixr links, but not enough
-- machine-readable event data to build shows without blocked Tixr pages.

WITH club_row AS (
    SELECT id
    FROM clubs
    WHERE name = 'Rose City Comedy'
)
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
    id,
    'tixr'::"ScrapingPlatform",
    'tixr',
    'https://rosecitycomedy.club',
    TRUE,
    0,
    jsonb_build_object(
        'task_2011_audit', jsonb_build_object(
            'status', 'blocked',
            'audited_at', '2026-05-08',
            'fetch_stack', 'scraper PlaywrightBrowser plus TixrClient/HttpClient paths',
            'venue_owned_pages_checked', jsonb_build_array(
                'https://rosecitycomedy.club',
                'https://rosecitycomedy.club/events',
                'https://rosecitycomedy.club/shows',
                'https://rosecitycomedy.club/calendar'
            ),
            'tixr_pages_checked', jsonb_build_array(
                'https://rosecitycomedy.tixr.com',
                'https://tixr.com/groups/rosecitycomedy',
                'https://rosecitycomedy.tixr.com/edbassmaster',
                'https://rosecitycomedy.tixr.com/openmic'
            ),
            'available_without_tixr_detail_fetch', jsonb_build_array(
                'ticket_url',
                'event_url',
                'poster_image_url',
                'partial_title_from_slug_or_image_filename'
            ),
            'missing_without_tixr_detail_fetch', jsonb_build_array(
                'machine_readable_date',
                'machine_readable_time'
            ),
            'blocker', 'Tixr group, event, and likely API paths return DataDome challenge HTML through scraper fetch paths without CAPTCHA/proxy support',
            'fallback_decision', 'No deterministic venue-page fallback: homepage links and poster images are insufficient without date/time'
        )
    ),
    NOW(),
    NOW()
FROM club_row
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = COALESCE(NULLIF(scraping_sources.source_url, ''), EXCLUDED.source_url),
    enabled = scraping_sources.enabled,
    metadata = COALESCE(scraping_sources.metadata, '{}'::jsonb) || EXCLUDED.metadata,
    updated_at = NOW();
