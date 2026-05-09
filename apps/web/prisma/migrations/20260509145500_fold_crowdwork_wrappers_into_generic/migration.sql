-- [TASK-2069] Fold thin Crowdwork venue wrapper scrapers into GenericCrowdworkScraper.

UPDATE scraping_sources ss
SET
    scraper_key = 'crowdwork',
    metadata = ss.metadata || '{"default_timezone":"America/Chicago","rails_to_iana":true}'::jsonb
FROM clubs c
WHERE ss.club_id = c.id
  AND c.name IN ('iO Theater', 'Logan Square Improv', 'The Backline')
  AND ss.platform = 'crowdwork'::"ScrapingPlatform"
  AND ss.scraper_key IN ('io_theater', 'logan_square_improv', 'the_backline');

UPDATE scraping_sources ss
SET
    scraper_key = 'crowdwork',
    metadata = ss.metadata || '{"default_timezone":"America/New_York","rails_to_iana":true}'::jsonb
FROM clubs c
WHERE ss.club_id = c.id
  AND c.name = 'Rails Comedy'
  AND ss.platform = 'crowdwork'::"ScrapingPlatform"
  AND ss.scraper_key = 'rails_comedy';

UPDATE scraping_sources ss
SET
    scraper_key = 'crowdwork',
    metadata = ss.metadata || '{"default_timezone":"America/New_York"}'::jsonb
FROM clubs c
WHERE ss.club_id = c.id
  AND c.name = 'Philly Improv Theater'
  AND ss.platform = 'crowdwork'::"ScrapingPlatform"
  AND ss.scraper_key = 'philly_improv_theater';
