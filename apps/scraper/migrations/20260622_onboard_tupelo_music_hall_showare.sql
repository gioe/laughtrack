-- TASK-3163: Onboard Tupelo Music Hall via accesso ShoWare.
--
-- Tupelo uses a white-label ShoWare host at tickets.tupelohall.com rather than
-- a showare.com subdomain. The ticket feed includes concerts and other events,
-- so metadata.include_title_patterns keeps the source scoped to comedy rows.

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
    club_type,
    google_place_id
)
SELECT
    'Tupelo Music Hall',
    '10 A Street',
    'https://www.tupelomusichall.com',
    '03038',
    'America/New_York',
    TRUE,
    'Derry',
    'NH',
    'active',
    'venue',
    'ChIJg4GEgqtT4okRLI5_Dg5-ffA'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJg4GEgqtT4okRLI5_Dg5-ffA'
        OR (lower(name) = lower('Tupelo Music Hall') AND lower(city) = lower('Derry') AND state = 'NH')
);

UPDATE clubs
   SET address = '10 A Street',
       website = 'https://www.tupelomusichall.com',
       zip_code = '03038',
       timezone = 'America/New_York',
       visible = TRUE,
       city = 'Derry',
       state = 'NH',
       status = 'active',
       club_type = 'venue',
       google_place_id = COALESCE(google_place_id, 'ChIJg4GEgqtT4okRLI5_Dg5-ffA')
 WHERE google_place_id = 'ChIJg4GEgqtT4okRLI5_Dg5-ffA'
    OR (lower(name) = lower('Tupelo Music Hall') AND lower(city) = lower('Derry') AND state = 'NH');

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
    'showare',
    'https://tickets.tupelohall.com/default.asp',
    0,
    TRUE,
    '{
        "showare_whitelabel": true,
        "list_page_size": 100,
        "include_title_patterns": [
            "comedy",
            "comedian",
            "Bob Marley",
            "Juston McKinney",
            "Lenny Clarke",
            "Tupelo Night of Comedy"
        ]
    }'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJg4GEgqtT4okRLI5_Dg5-ffA'
        OR (lower(c.name) = lower('Tupelo Music Hall') AND lower(c.city) = lower('Derry') AND c.state = 'NH'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'showare'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://tickets.tupelohall.com/default.asp',
       priority = 0,
       enabled = TRUE,
       metadata = '{
           "showare_whitelabel": true,
           "list_page_size": 100,
           "include_title_patterns": [
               "comedy",
               "comedian",
               "Bob Marley",
               "Juston McKinney",
               "Lenny Clarke",
               "Tupelo Night of Comedy"
           ]
       }'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'showare'
   AND (c.google_place_id = 'ChIJg4GEgqtT4okRLI5_Dg5-ffA'
        OR (lower(c.name) = lower('Tupelo Music Hall') AND lower(c.city) = lower('Derry') AND c.state = 'NH'));
