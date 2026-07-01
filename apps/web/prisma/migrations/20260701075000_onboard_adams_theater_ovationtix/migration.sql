-- Onboard The Adams Theater (Adams, MA) via generic OvationTix.
--
-- The user-provided comedy page (https://www.adamstheater.org/comedy) is a
-- Wix-rendered, comedy-filtered listing whose show tiles link to OvationTix
-- client 36681 productions. The Adams Theater is a mixed-use performing arts
-- venue, so metadata.comedy_filter=true keeps this source scoped to comedy when
-- the generic OvationTix scraper augments discovery from the client series view.

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    phone_number,
    visible,
    city,
    state,
    country,
    status,
    club_type
)
SELECT
    'The Adams Theater',
    '27 Park Street, Adams, MA 01220, USA',
    'https://www.adamstheater.org',
    '01220',
    'America/New_York',
    '888.401.5022',
    TRUE,
    'Adams',
    'MA',
    'US',
    'active',
    'venue'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE lower(name) = lower('The Adams Theater')
        OR lower(website) = lower('https://www.adamstheater.org')
        OR (
            lower(address) IN (
                lower('27 Park Street, Adams, MA 01220, USA'),
                lower('27 Park Street')
            )
            AND lower(city) = lower('Adams')
            AND state = 'MA'
        )
);

UPDATE clubs
   SET address = '27 Park Street, Adams, MA 01220, USA',
       website = 'https://www.adamstheater.org',
       zip_code = '01220',
       timezone = 'America/New_York',
       phone_number = '888.401.5022',
       visible = TRUE,
       city = 'Adams',
       state = 'MA',
       country = 'US',
       status = 'active',
       club_type = 'venue'
 WHERE lower(name) = lower('The Adams Theater')
    OR lower(website) = lower('https://www.adamstheater.org')
    OR (
        lower(address) IN (
            lower('27 Park Street, Adams, MA 01220, USA'),
            lower('27 Park Street')
        )
        AND lower(city) = lower('Adams')
        AND state = 'MA'
    );

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    ovationtix_id,
    priority,
    enabled,
    metadata
)
SELECT
    c.id,
    'ovationtix'::"ScrapingPlatform",
    'ovationtix',
    'https://www.adamstheater.org/comedy',
    '36681',
    0,
    TRUE,
    '{"comedy_filter": true}'::jsonb
  FROM clubs c
 WHERE lower(c.name) = lower('The Adams Theater')
   AND lower(c.city) = lower('Adams')
   AND c.state = 'MA'
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'ovationtix'
          AND s.ovationtix_id = '36681'
   );

UPDATE scraping_sources s
   SET platform = 'ovationtix'::"ScrapingPlatform",
       source_url = 'https://www.adamstheater.org/comedy',
       ovationtix_id = '36681',
       priority = 0,
       enabled = TRUE,
       metadata = '{"comedy_filter": true}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'ovationtix'
   AND s.ovationtix_id = '36681'
   AND lower(c.name) = lower('The Adams Theater')
   AND lower(c.city) = lower('Adams')
   AND c.state = 'MA';
