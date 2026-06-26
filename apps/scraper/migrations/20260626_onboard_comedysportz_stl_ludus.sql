-- TASK-3303: Onboard ComedySportz St. Louis (Maryland Heights, MO) via Ludus.
--
-- ComedySportz St. Louis (cszstlouis.com) is a dedicated improv-comedy venue
-- running weekly ComedySportz matches. Its own site only embeds the Ludus widget;
-- the real ticketing platform is Ludus (ludus.com), subdomain 'hatonahatcomedy'
-- (the venue's parent brand "Hat on a Hat Comedy"). Discovery platform hint was
-- "Ludus" — confirmed live.
--
-- Unlike Park Theatre (a mixed-use venue that tags comedy with category 468),
-- ComedySportz leaves data-event-categories EMPTY on every card because every
-- public show is comedy. So comedy_category_id is omitted (the extractor then
-- keeps ALL cards) and the public comedy shows are scoped with an
-- include_title_patterns allowlist. The embed currently lists "ComedySportz"
-- (the match) plus "Intro to Improv - 101" (a class); the allowlist keeps the
-- match and drops the class. The keyword comedy_filter is intentionally NOT used
-- here: select_comedy_titles drops "ComedySportz" yet keeps "Intro to Improv"
-- (matches the 'improv' keyword), i.e. exactly backwards for this venue.
-- Ludus title-pattern support added in TASK-3303.
--
-- visible=TRUE (fixed venue). Cloudflare managed challenge is cleared by the
-- scraper's curl_cffi impersonation.
--
-- Idempotent: matches on google_place_id or (lower name, city, state), and on
-- (club_id, scraper_key) for the source.

INSERT INTO clubs (
    name,
    address,
    website,
    zip_code,
    timezone,
    visible,
    city,
    state,
    country,
    status,
    club_type,
    google_place_id
)
SELECT
    'ComedySportz St. Louis',
    '2443 Creve Coeur Mill Rd',
    'https://www.cszstlouis.com/',
    '63043',
    'America/Chicago',
    TRUE,
    'Maryland Heights',
    'MO',
    'US',
    'active',
    'club',
    'ChIJ___jUlQu34cRe1R7j5IYVDk'
WHERE NOT EXISTS (
    SELECT 1
      FROM clubs
     WHERE google_place_id = 'ChIJ___jUlQu34cRe1R7j5IYVDk'
        OR (lower(name) = lower('ComedySportz St. Louis') AND lower(city) = lower('Maryland Heights') AND state = 'MO')
);

UPDATE clubs
   SET address = '2443 Creve Coeur Mill Rd',
       website = 'https://www.cszstlouis.com/',
       zip_code = '63043',
       timezone = 'America/Chicago',
       visible = TRUE,
       city = 'Maryland Heights',
       state = 'MO',
       country = 'US',
       status = 'active',
       club_type = 'club',
       google_place_id = COALESCE(google_place_id, 'ChIJ___jUlQu34cRe1R7j5IYVDk')
 WHERE google_place_id = 'ChIJ___jUlQu34cRe1R7j5IYVDk'
    OR (lower(name) = lower('ComedySportz St. Louis') AND lower(city) = lower('Maryland Heights') AND state = 'MO');

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
    'ludus',
    'https://hatonahatcomedy.ludus.com/',
    0,
    TRUE,
    '{"ludus_subdomain": "hatonahatcomedy", "include_title_patterns": ["ComedySportz"]}'::jsonb
  FROM clubs c
 WHERE (c.google_place_id = 'ChIJ___jUlQu34cRe1R7j5IYVDk'
        OR (lower(c.name) = lower('ComedySportz St. Louis') AND lower(c.city) = lower('Maryland Heights') AND c.state = 'MO'))
   AND NOT EXISTS (
       SELECT 1
         FROM scraping_sources s
        WHERE s.club_id = c.id
          AND s.scraper_key = 'ludus'
   );

UPDATE scraping_sources s
   SET platform = 'custom'::"ScrapingPlatform",
       source_url = 'https://hatonahatcomedy.ludus.com/',
       priority = 0,
       enabled = TRUE,
       metadata = '{"ludus_subdomain": "hatonahatcomedy", "include_title_patterns": ["ComedySportz"]}'::jsonb,
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND s.scraper_key = 'ludus'
   AND (c.google_place_id = 'ChIJ___jUlQu34cRe1R7j5IYVDk'
        OR (lower(c.name) = lower('ComedySportz St. Louis') AND lower(c.city) = lower('Maryland Heights') AND c.state = 'MO'));
