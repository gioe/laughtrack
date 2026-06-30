-- TASK-3521: Re-probe json_ld venues whose enabled sources stopped yielding
-- upcoming shows. No scraper code change is needed: each source still points at
-- the correct public venue-owned page for its platform, but current venue-side
-- content is either dormant/stale or, for Hive, already healthy again.

UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_3521_disposition', jsonb_build_object(
            'probed_at', '2026-06-30',
            'disposition', 'confirmed_dormant_stale_public_calendar',
            'source_checked', 'https://www.tribecacomedyclub.com/calendar',
            'result', 'Official calendar source still returns only 2 stale JSON-LD ComedyEvent rows from 2026-06-06; /calendar/2026-07 through /calendar/2026-09 contain no JSON-LD events or event detail links; /site-maps/upcoming-events is empty.',
            'action', 'left enabled so future venue-side calendar updates are picked up automatically; no alternate public feed found'
        )
    ),
    updated_at = NOW()
WHERE club_id = 48
  AND scraper_key = 'json_ld';

UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_3521_disposition', jsonb_build_object(
            'probed_at', '2026-06-30',
            'disposition', 'confirmed_dormant_stale_public_calendar',
            'source_checked', 'https://www.darkhorsecomedyclub.com/calendar',
            'result', 'Official calendar source still returns only 2 stale JSON-LD ComedyEvent rows from 2026-06-06; /calendar/2026-07 through /calendar/2026-09 contain no JSON-LD events or event detail links; /site-maps/upcoming-events is empty.',
            'action', 'left enabled so future venue-side calendar updates are picked up automatically; no alternate public feed found'
        )
    ),
    updated_at = NOW()
WHERE club_id = 49
  AND scraper_key = 'json_ld';

UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_3521_disposition', jsonb_build_object(
            'probed_at', '2026-06-30',
            'disposition', 'confirmed_dormant_stale_public_calendar',
            'source_checked', 'https://www.midtowncomedyclub.com/calendar',
            'result', 'Official calendar source still returns only 2 stale JSON-LD ComedyEvent rows from 2026-06-06; /calendar/2026-07 through /calendar/2026-09 contain no JSON-LD events or event detail links; /site-maps/upcoming-events is empty.',
            'action', 'left enabled so future venue-side calendar updates are picked up automatically; no alternate public feed found'
        )
    ),
    updated_at = NOW()
WHERE club_id = 50
  AND scraper_key = 'json_ld';

UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_3521_disposition', jsonb_build_object(
            'probed_at', '2026-06-30',
            'disposition', 'confirmed_dormant_empty_city_showtimes_page',
            'source_checked', 'https://www.thedinnerdetective.com/st-paul/murder-mystery-tickets-showtimes/',
            'result', 'Correct Dinner Detective city showtimes URL loads HTTP 200 but currently renders no TheaterEvent JSON-LD blocks; scraper returns 0 shows without bot-block symptoms.',
            'action', 'left enabled so future St. Paul showtimes reappear automatically'
        )
    ),
    updated_at = NOW()
WHERE club_id = 11438
  AND scraper_key = 'json_ld';

UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_3521_disposition', jsonb_build_object(
            'probed_at', '2026-06-30',
            'disposition', 'source_healthy_detail_fetch',
            'source_checked', 'https://www.pompanobeacharts.org/events',
            'result', 'Configured detail_fetch discovered 66 detail pages; location_name_filter plus comedy_filter produced 1 upcoming Live at the Hive comedy show. Existing source URL and metadata remain correct.',
            'action', 'no source change'
        )
    ),
    updated_at = NOW()
WHERE club_id = 11459
  AND scraper_key = 'json_ld';
