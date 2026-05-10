-- [TASK-2109] Opt Laugh Factory Covina into the guarded Tixr group-events API fallback.
--
-- TASK-2103 captured that the group page is DataDome-blocked in runner-class
-- egress while a headed browser showed future inventory. The browser app uses
-- /api/groups/{group_id}/events; 1613 is the observed Covina group id.

UPDATE scraping_sources ss
SET
    metadata = COALESCE(ss.metadata, '{}'::jsonb)
        || jsonb_build_object(
            'tixr_group_id', '1613',
            'tixr_group_events_api_fallback', true,
            'task_2109_group_api_fallback', jsonb_build_object(
                'status', 'enabled',
                'enabled_at', '2026-05-10',
                'group_id', '1613',
                'reason', 'Use guarded direct Tixr group-events API fallback when DataDome blocks the group page fetch.'
            )
        ),
    updated_at = NOW()
FROM clubs c
WHERE c.id = ss.club_id
  AND c.id = 171
  AND ss.scraper_key = 'tixr'
  AND ss.priority = 0;

-- Rose City's venue-owned pages expose Tixr links but no event dates; the
-- fallback can query the group-events endpoint directly from the configured
-- group slug when the page path cannot produce deterministic events.
UPDATE scraping_sources ss
SET
    enabled = TRUE,
    metadata = COALESCE(ss.metadata, '{}'::jsonb)
        || jsonb_build_object(
            'tixr_group_slug', 'rosecitycomedy',
            'tixr_group_events_api_fallback', true,
            'task_2109_group_api_fallback', jsonb_build_object(
                'status', 'enabled',
                'enabled_at', '2026-05-10',
                'group_slug', 'rosecitycomedy',
                'reason', 'Use guarded direct Tixr group-events API fallback when venue-owned pages cannot provide machine-readable date/time.'
            )
        ),
    updated_at = NOW()
FROM clubs c
WHERE c.id = ss.club_id
  AND c.id = 1023
  AND ss.scraper_key = 'tixr'
  AND ss.priority = 0;
