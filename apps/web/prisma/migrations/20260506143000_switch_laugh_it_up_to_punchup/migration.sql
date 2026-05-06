-- TASK-1969: Restore LAUGH IT UP COMEDY CLUB coverage through the venue's
-- primary Punchup calendar. TASK-1943 disabled the stale TicketWeb source
-- after the site migrated away from the WordPress TicketWeb plugin.
--
-- SeatEngine ss=822 remains disabled: it was only a fallback mirror, and the
-- venue-owned calendar now exposes the canonical lineup via Punchup.

UPDATE scraping_sources
SET enabled = FALSE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_1969_disposition',
        jsonb_build_object(
            'kind', 'stale_ticketweb_replaced_by_punchup',
            'rationale', 'Venue-owned calendar at https://www.laughitupcomedy.com/calendar is powered by Punchup; keep stale TicketWeb row disabled and add custom Punchup source.'
        )
    ),
    updated_at = NOW()
WHERE id = 313
  AND club_id = 485
  AND platform = 'ticketweb';

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
    485,
    'custom',
    'laugh_it_up_comedy',
    'https://www.laughitupcomedy.com/calendar',
    TRUE,
    0,
    jsonb_build_object(
        'task_1969_source',
        jsonb_build_object(
            'kind', 'punchup_primary_calendar',
            'seatengine_fallback_decision', 'Do not re-enable ss=822: Punchup carries the venue-owned public lineup and is the canonical source.'
        )
    ),
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE club_id = 485
      AND platform = 'custom'
      AND priority = 0
);

UPDATE scraping_sources
SET scraper_key = 'laugh_it_up_comedy',
    source_url = 'https://www.laughitupcomedy.com/calendar',
    enabled = TRUE,
    metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_1969_source',
        jsonb_build_object(
            'kind', 'punchup_primary_calendar',
            'seatengine_fallback_decision', 'Do not re-enable ss=822: Punchup carries the venue-owned public lineup and is the canonical source.'
        )
    ),
    updated_at = NOW()
WHERE club_id = 485
  AND platform = 'custom'
  AND priority = 0;

UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
        'task_1969_fallback_decision',
        jsonb_build_object(
            'kind', 'fallback_rejected',
            'rationale', 'Leave SeatEngine disabled because the venue-owned Punchup calendar is the canonical primary source.'
        )
    ),
    updated_at = NOW()
WHERE id = 822
  AND club_id = 485
  AND platform = 'seatengine';

UPDATE clubs
SET website = 'https://www.laughitupcomedy.com',
    timezone = COALESCE(timezone, 'America/New_York')
WHERE id = 485;
