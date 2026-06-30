-- Switch House of Comedy British Columbia from Webflow homepage cards to the
-- richer Pixl Calendar API source. The homepage exposes only a small card
-- subset with unknown prices; Pixl exposes the full inventory and sales tiers.

UPDATE scraping_sources s
   SET scraper_key = 'tixr',
       source_url = 'https://www.pixlcalendar.com/api/events/house-of-comedy-bc',
       enabled = TRUE,
       metadata = jsonb_build_object(
           'backend', 'Pixl Calendar API',
           'ticketing', 'Tixr groups/comicstripbc event links',
           'calendar_url', 'https://www.pixlcalendar.com/house-of-comedy-bc',
           'previous_source_url', 'https://bc.houseofcomedy.net/',
           'previous_scraper_key', 'tixr_webflow_day_card',
           'tixr_source_type', 'pixl_calendar_api',
           'datadome_dependent', false,
           'tixr_group_fragment', 'tixr.com/groups/comicstripbc/events/',
           'detail_fetch_required', false,
           'pixl_calendar_api_url', 'https://www.pixlcalendar.com/api/events/house-of-comedy-bc',
           'task_20260629_pixl_calendar', jsonb_build_object(
               'reason', 'Use Pixl Calendar JSON for full House of Comedy BC inventory and sale-tier prices without Tixr detail-page fetches.',
               'status', 'enabled',
               'enabled_at', '2026-06-29'
           )
       ),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.id = 2357
   AND lower(c.name) = lower('House of Comedy British Columbia')
   AND s.priority = 0;
