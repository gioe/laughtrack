-- [TASK-2109] Clean up Tixr DataDome mitigation metadata after verification.
--
-- Covina now has a working numeric group-events fallback, so the old
-- TASK-2103 blocked-audit annotation is stale. Rose City remains unresolved:
-- its slug is not accepted by the group-events API, so TASK-2125 owns numeric
-- group-id discovery or alternate source onboarding while task_2011_audit stays.

UPDATE scraping_sources ss
SET
    metadata = COALESCE(ss.metadata, '{}'::jsonb) - 'task_2103_audit',
    updated_at = NOW()
FROM clubs c
WHERE c.id = ss.club_id
  AND c.id = 171
  AND ss.scraper_key = 'tixr'
  AND ss.priority = 0;

UPDATE scraping_sources ss
SET
    enabled = FALSE,
    metadata = COALESCE(ss.metadata, '{}'::jsonb)
        - 'tixr_group_slug'
        - 'tixr_group_events_api_fallback'
        - 'task_2109_group_api_fallback',
    updated_at = NOW()
FROM clubs c
WHERE c.id = ss.club_id
  AND c.id = 1023
  AND ss.scraper_key = 'tixr'
  AND ss.priority = 0;
