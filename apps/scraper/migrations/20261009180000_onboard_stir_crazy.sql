-- TASK-4148: preserve canonical venue identity and hidden state until live ingestion.
UPDATE clubs
SET website = 'https://www.stircrazycomedyclub.com/',
    address = '6751 N Sunset Blvd, Ste E-206, Glendale, AZ 85305',
    timezone = 'America/Phoenix',
    latitude = 33.5335572, longitude = -112.2616635
WHERE id = 17393;

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT id, 'custom'::"ScrapingPlatform", 'stir_crazy',
       'https://www.stircrazycomedyclub.com/calendar', 0, TRUE, '{}'::jsonb
FROM clubs WHERE id = 17393
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key, source_url = EXCLUDED.source_url,
    enabled = TRUE, updated_at = NOW();
