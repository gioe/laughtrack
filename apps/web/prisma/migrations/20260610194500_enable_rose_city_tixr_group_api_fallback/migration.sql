-- [TASK-2125] Opt Rose City Comedy into the guarded Tixr group-events API fallback.
--
-- TASK-2109 left Rose City unresolved because its numeric Tixr group id was
-- unknown: the slug 'rosecitycomedy' returns 400 from the group-events API and
-- bounded numeric scans were indistinguishable from misses behind DataDome 403s.
-- A headed-browser network inspection of tixr.com/groups/rosecitycomedy on
-- 2026-06-10 shows the page consuming /api/groups/2444/events; a scraper-stack
-- probe of TixrClient.fetch_group_events('2444') returned 19 future events.
--
-- Re-enable the source with the numeric group id, and drop the stale
-- blocked-audit annotation (task_2011_audit) and the disable-disposition
-- record (task_2104_disposition) that documented the now-resolved DataDome
-- dead end. tixr_source_type / datadome_dependent / detail_fetch_required are
-- kept: they describe the page-scrape path, which remains DataDome-blocked —
-- only the group-events API fallback bypasses it.
--
-- source_url moves from the venue homepage to the Tixr group page, matching
-- the working Covina (club 171) configuration. The venue homepage fetch
-- succeeds and extracts per-event Tixr detail URLs, whose extraction failures
-- (all DataDome-blocked) do NOT consult the group-events API fallback — the
-- fallback only fires when the calendar page itself yields no HTML/URLs,
-- which is the deterministic outcome for the DataDome-blocked group page.

UPDATE scraping_sources ss
SET
    enabled = TRUE,
    source_url = 'https://www.tixr.com/groups/rosecitycomedy',
    metadata = (COALESCE(ss.metadata, '{}'::jsonb)
        - 'task_2011_audit'
        - 'task_2104_disposition')
        || jsonb_build_object(
            'tixr_group_id', '2444',
            'tixr_group_events_api_fallback', true,
            'task_2125_group_api_fallback', jsonb_build_object(
                'status', 'enabled',
                'enabled_at', '2026-06-10',
                'group_id', '2444',
                'reason', 'Numeric group id discovered via headed-browser network inspection of the Tixr group page; group-events API fallback verified returning 19 future events through the scraper stack.'
            )
        ),
    updated_at = NOW()
FROM clubs c
WHERE c.id = ss.club_id
  AND c.id = 1023
  AND ss.scraper_key = 'tixr'
  AND ss.priority = 0;
