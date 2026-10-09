-- TASK-4146: the official calendar now sells through Tixologi, not SeatEngine.
-- Retain the canonical venue and its historical SeatEngine source/identity.
UPDATE clubs
SET website = 'https://www.ricomedyconnection.com', timezone = 'America/New_York'
WHERE id = 217;

UPDATE scraping_sources
SET enabled = FALSE, updated_at = NOW()
WHERE id = 64 AND club_id = 217 AND platform = 'seatengine';

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled)
SELECT id, 'custom'::"ScrapingPlatform", 'comedy_connection',
       'https://www.ricomedyconnection.com/events', 0, TRUE
FROM clubs WHERE id = 217
ON CONFLICT (club_id, platform, priority) DO UPDATE
SET scraper_key = EXCLUDED.scraper_key,
    source_url = EXCLUDED.source_url,
    enabled = TRUE,
    updated_at = NOW();
