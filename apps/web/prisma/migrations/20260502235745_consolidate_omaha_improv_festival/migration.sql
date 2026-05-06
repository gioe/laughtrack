-- Consolidate duplicate Omaha festival records.
--
-- Club 1474 ("Omaha Improv Festival (Shows)") is a stale SeatEngine-imported
-- duplicate. SeatEngine venue 193 still exists but returns 0 upcoming shows.
-- The official site now brands the event as Omaha Comedy Fest and lists a
-- multi-venue festival schedule with fragmented ticketing across multiple
-- platforms, so there is no unified SeatEngine scraper to adopt.

UPDATE clubs
SET
    website = 'https://www.omahacomedyfest.com',
    city = 'Omaha',
    state = 'NE',
    country = 'US',
    timezone = 'America/Chicago',
    club_type = 'festival',
    visible = false,
    status = 'active',
    closed_at = NULL
WHERE id = 784;

UPDATE scraping_sources
SET
    platform = 'custom',
    scraper_key = 'disabled',
    external_id = NULL,
    source_url = 'https://www.omahacomedyfest.com',
    enabled = false
WHERE club_id = 784;

UPDATE clubs
SET
    website = 'https://www.omahacomedyfest.com',
    city = 'Omaha',
    state = 'NE',
    country = 'US',
    timezone = 'America/Chicago',
    club_type = 'festival',
    visible = false,
    status = 'closed',
    closed_at = COALESCE(closed_at, now())
WHERE id = 1474;

UPDATE scraping_sources
SET
    platform = 'custom',
    scraper_key = 'disabled',
    external_id = NULL,
    source_url = 'https://www.omahacomedyfest.com',
    enabled = false
WHERE club_id = 1474;
