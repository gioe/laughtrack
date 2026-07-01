-- Onboard Great Outdoors Comedy Festival Halifax as a separate Tixr public-card source.
--
-- The direct Tixr event URL for Halifax is DataDome-blocked from scraper egress:
-- https://www.tixr.com/groups/gocf/events/great-outdoors-comedy-festival-2026-halifax-152718?sort=RECOMMENDED&COL=16248&A=L
--
-- The festival-owned Halifax city page renders complete Webflow show cards with Halifax
-- date/time, lineup, and Tixr ticket URLs. The tixr_public_card scraper reads
-- those cards directly and avoids fetching Tixr detail pages.

INSERT INTO clubs (
    name,
    address,
    website,
    timezone,
    visible,
    city,
    state,
    country,
    status,
    club_type
)
SELECT
    'Great Outdoors Comedy Festival Halifax',
    'Garrison Grounds, Halifax, NS, Canada',
    'https://www.greatoutdoorscomedyfestival.com/cities/halifax',
    'America/Halifax',
    TRUE,
    'Halifax',
    'NS',
    'CA',
    'active',
    'festival'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('Great Outdoors Comedy Festival Halifax')
        OR (
            lower(address) = lower('Garrison Grounds, Halifax, NS, Canada')
            AND lower(city) = lower('Halifax')
            AND state = 'NS'
        )
);

UPDATE clubs
   SET address = 'Garrison Grounds, Halifax, NS, Canada',
       website = 'https://www.greatoutdoorscomedyfestival.com/cities/halifax',
       timezone = 'America/Halifax',
       visible = TRUE,
       city = 'Halifax',
       state = 'NS',
       country = 'CA',
       status = 'active',
       club_type = 'festival'
 WHERE lower(name) = lower('Great Outdoors Comedy Festival Halifax')
    OR (
        lower(address) = lower('Garrison Grounds, Halifax, NS, Canada')
        AND lower(city) = lower('Halifax')
        AND state = 'NS'
    );

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
    'tixr'::"ScrapingPlatform",
    'tixr_public_card',
    'https://www.greatoutdoorscomedyfestival.com/cities/halifax',
    0,
    TRUE,
    '{"gocf_city": "Halifax"}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('Great Outdoors Comedy Festival Halifax')
   AND lower(c.city) = lower('Halifax')
   AND c.state = 'NS'
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'tixr_public_card'
          AND s.source_url = 'https://www.greatoutdoorscomedyfestival.com/cities/halifax'
   );

UPDATE scraping_sources s
   SET platform = 'tixr'::"ScrapingPlatform",
       source_url = 'https://www.greatoutdoorscomedyfestival.com/cities/halifax',
       priority = 0,
       enabled = TRUE,
       metadata = '{"gocf_city": "Halifax"}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'tixr_public_card'
   AND lower(c.name) = lower('Great Outdoors Comedy Festival Halifax')
   AND lower(c.city) = lower('Halifax')
   AND c.state = 'NS';
