-- Onboard The Newport Theater via the generic Eventbrite scraper - TASK-2989
--
-- The Newport Theater (956 W Newport Ave, Chicago, IL 60657) is a fringe/variety
-- comedy venue in Lakeview discovered via discover-comedy-venues near 60601. Its
-- own Wix site (http://www.newporttheater.com/) hydrates listings entirely from a
-- single Eventbrite organizer feed (organizer_id 32014204641: improv, Edinburgh
-- Fringe previews, music-improv, and burlesque/variety shows).
--
-- Single-venue mode is used deliberately: the organizer registers events under
-- several Eventbrite venue_ids that all resolve to the same physical address, so
-- the source_url intentionally omits "/o/" to keep every Show attached to this one
-- club rather than letting organizer-mode split them into multiple per-venue clubs.
-- The eventbrite scraper tries the venue endpoint, 404s, then falls back to the
-- organizer endpoint (EventbriteClient.fetch_all_events).
--
-- Verified on 2026-06-19: the organizer feed returned 36 live events; a real
-- scrape persisted 34 shows for club 9091 (Jun–Oct 2026).

INSERT INTO clubs (
    name,
    address,
    website,
    city,
    state,
    zip_code,
    timezone,
    country,
    club_type,
    google_place_id,
    visible,
    status
)
SELECT
    'The Newport Theater',
    '956 W Newport Ave, Chicago, IL 60657',
    'http://www.newporttheater.com/',
    'Chicago',
    'IL',
    '60657',
    'America/Chicago',
    'US',
    'club',
    'ChIJo_1z7a3TD4gR8wH2-YBxQuI',
    TRUE,
    'active'
WHERE NOT EXISTS (
    SELECT 1
    FROM clubs
    WHERE google_place_id = 'ChIJo_1z7a3TD4gR8wH2-YBxQuI'
       OR name = 'The Newport Theater'
);

INSERT INTO scraping_sources (
    club_id,
    platform,
    scraper_key,
    source_url,
    eventbrite_id,
    enabled,
    priority,
    metadata,
    created_at,
    updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com',
    '32014204641',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJo_1z7a3TD4gR8wH2-YBxQuI' OR c.name = 'The Newport Theater')
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.scraper_key = 'eventbrite'
  );
