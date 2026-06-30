-- Switch Venetian comedy venue scraping from Ticketmaster Discovery to the
-- venue-owned AEM entertainment page/persisted GraphQL feed.

UPDATE clubs
   SET website = 'https://www.venetianlasvegas.com/entertainment.html'
 WHERE id IN (4826, 4870)
   AND COALESCE(website, '') = '';

UPDATE scraping_sources
   SET platform = 'custom',
       scraper_key = 'venetian_entertainment',
       source_url = 'https://www.venetianlasvegas.com/entertainment.html',
       enabled = TRUE,
       metadata = CASE club_id
           WHEN 4826 THEN jsonb_build_object(
               'backend', 'Venetian AEM persisted GraphQL',
               'previous_platform', 'ticketmaster',
               'previous_scraper_key', 'ticketmaster_comedy',
               'previous_source_url', 'https://www.ticketmaster.com',
               'graphql_query', 'venetian/allEntertainment',
               'venue_category', 'the-palazzo-theatre',
               'comedy_category', 'comedy',
               'detail_fetch_required', false,
               'task_20260629_venetian_entertainment', jsonb_build_object(
                   'reason', 'Use Venetian-owned entertainment page as the canonical source and filter comedy by AEM categories.',
                   'status', 'enabled',
                   'enabled_at', '2026-06-29'
               )
           )
           WHEN 4870 THEN jsonb_build_object(
               'backend', 'Venetian AEM persisted GraphQL',
               'previous_platform', 'ticketmaster',
               'previous_scraper_key', 'ticketmaster_comedy',
               'previous_source_url', 'https://www.ticketmaster.com',
               'graphql_query', 'venetian/allEntertainment',
               'venue_category', 'the-venetian-theatre',
               'comedy_category', 'comedy',
               'detail_fetch_required', false,
               'task_20260629_venetian_entertainment', jsonb_build_object(
                   'reason', 'Use Venetian-owned entertainment page as the canonical source and filter comedy by AEM categories.',
                   'status', 'enabled',
                   'enabled_at', '2026-06-29'
               )
           )
           ELSE metadata
       END,
       ticketmaster_id = NULL,
       updated_at = NOW()
 WHERE club_id IN (4826, 4870)
   AND priority = 0;
