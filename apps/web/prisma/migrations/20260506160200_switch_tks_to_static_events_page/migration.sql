-- TASK-1981: Restore TK's (club 63) coverage through the current public
-- Spothopper events page. SeatEngine venue 514 remains disabled because it
-- returned no events, while the venue-owned events page exposes a ticketed
-- upcoming stand-up comedy event.

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_1981_fallback_decision',
        jsonb_build_object(
            'kind', 'stale_seatengine_rejected',
            'rationale', 'SeatEngine venue 514 returned no events; use the venue-owned Spothopper events page instead.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 63
  AND platform = 'seatengine'
  AND external_id = '514';

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    external_id,
    source_url,
    enabled,
    priority,
    metadata,
    created_at,
    updated_at
)
SELECT
    63,
    'custom',
    'tks_comedy',
    NULL,
    'https://www.tkscomedy.com/dallas-addison-tk-s-comedy-events',
    TRUE,
    0,
    jsonb_build_object(
        'task_1981_source',
        jsonb_build_object(
            'kind', 'spothopper_static_events_page',
            'verified_event', 'Mother''s Day Soiree live stand-up comedy show on 2026-05-10 at 1:00 PM America/Chicago'
        )
    ),
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 63
      AND platform = 'custom'
      AND priority = 0
);

UPDATE scraping_sources
SET scraper_key = 'tks_comedy',
    external_id = NULL,
    source_url = 'https://www.tkscomedy.com/dallas-addison-tk-s-comedy-events',
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_1981_source',
        jsonb_build_object(
            'kind', 'spothopper_static_events_page',
            'verified_event', 'Mother''s Day Soiree live stand-up comedy show on 2026-05-10 at 1:00 PM America/Chicago'
        )
    ),
    updated_at = NOW()
WHERE club_id = 63
  AND platform = 'custom'
  AND priority = 0;
