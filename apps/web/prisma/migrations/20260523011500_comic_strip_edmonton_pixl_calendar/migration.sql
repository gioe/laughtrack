-- [TASK-2409] Route Comic Strip Edmonton through Pixl Calendar JSON.
--
-- The Webflow homepage day-card surface only exposes the rendered subset of
-- Tixr links and no prices. Pixl Calendar's API exposes the full event
-- inventory with Tixr ticket URLs and sale-tier prices, so this source now
-- uses the generic Tixr scraper's Pixl JSON path.

UPDATE scraping_sources ss
SET
    scraper_key = 'tixr',
    source_url = 'https://www.pixlcalendar.com/api/events/comic-strip-edmonton',
    metadata = COALESCE(ss.metadata, '{}'::jsonb)
        || jsonb_build_object(
            'pixl_calendar_api_url', 'https://www.pixlcalendar.com/api/events/comic-strip-edmonton',
            'tixr_source_type', 'pixl_calendar_api',
            'detail_fetch_required', false,
            'datadome_dependent', false,
            'task_2409_pixl_calendar', jsonb_build_object(
                'status', 'enabled',
                'enabled_at', '2026-05-23',
                'reason', 'Use Pixl Calendar JSON for full Comic Strip Edmonton inventory and sale-tier prices without Tixr detail-page fetches.'
            )
        ),
    updated_at = NOW()
FROM clubs c
WHERE c.id = ss.club_id
  AND c.name = 'The Comic Strip West Edmonton Mall'
  AND ss.platform = 'custom'::"ScrapingPlatform"
  AND ss.scraper_key = 'tixr_webflow_day_card'
  AND ss.priority = 0;
