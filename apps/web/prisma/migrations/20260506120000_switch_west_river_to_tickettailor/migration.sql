-- TASK-1946: West River Comedy Club moved event publishing from Wix Events to TicketTailor.
UPDATE scraping_sources
SET enabled = false
WHERE club_id = (
    SELECT id
    FROM clubs
    WHERE name = 'West River Comedy Club'
)
AND platform = 'wix_events'::"ScrapingPlatform";

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled
)
SELECT
    clubs.id,
    'custom'::"ScrapingPlatform",
    'west_river_comedy',
    'https://www.tickettailor.com/events/westrivercomedyclub',
    0,
    true
FROM clubs
WHERE clubs.name = 'West River Comedy Club'
AND NOT EXISTS (
    SELECT 1
    FROM scraping_sources
    WHERE scraping_sources.club_id = clubs.id
    AND scraping_sources.scraper_key = 'west_river_comedy'
);

UPDATE scraping_sources
SET
    source_url = 'https://www.tickettailor.com/events/westrivercomedyclub',
    enabled = true
WHERE club_id = (
    SELECT id
    FROM clubs
    WHERE name = 'West River Comedy Club'
)
AND scraper_key = 'west_river_comedy';
