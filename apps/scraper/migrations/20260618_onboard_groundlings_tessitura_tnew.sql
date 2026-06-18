-- Onboard The Groundlings to the generic Tessitura TNEW production-seasons scraper.

UPDATE scraping_sources
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://purchase.groundlings.com/events?view=list',
       priority = 0,
       enabled = TRUE,
       metadata = '{"org":"GTAS","events_url":"https://purchase.groundlings.com/events?view=list","api_url":"https://purchase.groundlings.com/api/products/productionseasons"}'::jsonb
 WHERE club_id = 8836
   AND scraper_key = 'tessitura_tnew';

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT 8836,
       'custom'::"ScrapingPlatform",
       'tessitura_tnew',
       'https://purchase.groundlings.com/events?view=list',
       0,
       TRUE,
       '{"org":"GTAS","events_url":"https://purchase.groundlings.com/events?view=list","api_url":"https://purchase.groundlings.com/api/products/productionseasons"}'::jsonb
 WHERE NOT EXISTS (
       SELECT 1
         FROM scraping_sources
        WHERE club_id = 8836
          AND scraper_key = 'tessitura_tnew'
 );

UPDATE clubs
   SET visible = TRUE,
       website = 'https://groundlings.com/',
       scraping_url = 'https://purchase.groundlings.com/events?view=list',
       timezone = 'America/Los_Angeles'
 WHERE id = 8836;
