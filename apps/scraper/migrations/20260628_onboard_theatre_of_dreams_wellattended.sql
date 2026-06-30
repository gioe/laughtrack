-- TASK-3471: Onboard Theatre of Dreams Arts & Event Center via the net-new
-- WellAttended scraper.
--
-- Theatre of Dreams (amazingshows.com, a Castle Rock CO comedy/variety brand)
-- stages its public ticketed shows at The Magic Manor (5450 Manhart Ave,
-- Sedalia, CO 80135) and sells them through WellAttended, a Next.js RSC
-- ticketing platform: amazingshows.com -> theatreofdreams.wellattended.com. The
-- club is located at the actual show venue (Sedalia) so geo-discovery points
-- users to where the comedy is; the brand name is retained.
--
-- Comedy/variety confirmed with a dated calendar: David Deeble (comedy juggler,
-- Aug 7-8 2026), Chipper Lowell "Comedy & Magic Collide" (stand-up/improv/magic,
-- Aug 21-22 2026). Each /events/<slug> detail page embeds its occurrence +
-- ticket-tier data in the self.__next_f.push(...) RSC flight (no JSON-LD).
--
-- platform = 'custom' (WellAttended is not a ScrapingPlatform enum value);
-- scraper_key = 'wellattended' selects the new generic scraper. source_url is
-- the venue's WellAttended root; the scraper enumerates /events/<slug> pages
-- from it. Verified 4 upcoming shows.
--
-- Idempotent (re-runs nightly via bin/migrate): INSERT ... WHERE NOT EXISTS +
-- guarded UPDATE matched on lower(name); the scraping_sources guard keys on the
-- (club_id, platform, priority) unique constraint.

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    visible,
    city,
    state,
    status,
    club_type
)
SELECT
    'Theatre of Dreams Arts and Event Center',
    '5450 Manhart Ave',
    'https://www.amazingshows.com/',
    '80135',
    'America/Denver',
    TRUE,
    'Sedalia',
    'CO',
    'active',
    'club'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
     WHERE lower(name) = lower('Theatre of Dreams Arts and Event Center')
);

UPDATE clubs
   SET address = '5450 Manhart Ave',
       website = 'https://www.amazingshows.com/',
       zip_code = '80135',
       timezone = 'America/Denver',
       visible = TRUE,
       city = 'Sedalia',
       state = 'CO',
       status = 'active',
       club_type = 'club'
 WHERE lower(name) = lower('Theatre of Dreams Arts and Event Center');

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    priority,
    enabled,
    metadata
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'wellattended',
    'https://theatreofdreams.wellattended.com/',
    0,
    TRUE,
    '{}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('Theatre of Dreams Arts and Event Center')
   AND NOT EXISTS (
       SELECT 1 FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.platform = 'custom'::"ScrapingPlatform"
          AND s.priority = 0
   );

UPDATE scraping_sources s
   SET scraper_key = 'wellattended',
       source_url = 'https://theatreofdreams.wellattended.com/',
       enabled = TRUE,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.platform = 'custom'::"ScrapingPlatform"
   AND s.priority = 0
   AND lower(c.name) = lower('Theatre of Dreams Arts and Event Center');
