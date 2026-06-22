-- Onboard two more Boston-cluster comedy venues discovered via
-- discover-comedy-venues near ZIP 02101 - TASK-3151 (second batch).
--
-- 3. Union Comedy (593 Somerville Ave, Somerville, MA 02143) — Boston home for
--    longform improv. Ticketing/calendar is Crowdwork (account slug 'unioncomedy',
--    single theatre id 523). The "Union Comedy Training Center" Cambridge Google
--    listing is a future/under-construction space with no separate feed today, so
--    this is wired as ONE club. Verified 2026-06-21: a real scrape persisted 243
--    shows for club 10945.
--
-- 4. Stand Up Stick Up Comedy Club (25 Exchange St, Lynn, MA 01901) — recurring
--    stand-up series at The Neal Rantoul Vault Theatre. Tickets via the Eventbrite
--    organizer "Lynn Music Foundation" (id 59005476163). NOTE: that organizer is a
--    single physical venue but mixes the comedy series with free music/jam events,
--    so this source pulls some non-comedy events until a per-source title filter
--    exists. Verified 2026-06-21: a real scrape persisted 13 shows for club 10946.

-- ---- Union Comedy (Crowdwork) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Union Comedy', '593 Somerville Ave', 'http://www.unioncomedy.com/',
    'Somerville', 'MA', '02143', 'America/New_York', 'US', 'club',
    'ChIJwYodAhl344kRbCUo789bQXY', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJwYodAhl344kRbCUo789bQXY'
       OR name = 'Union Comedy'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'crowdwork'::"ScrapingPlatform",
    'crowdwork',
    'https://crowdwork.com/api/v2/unioncomedy/shows',
    TRUE,
    0,
    '{"rails_to_iana":true,"default_timezone":"America/New_York"}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJwYodAhl344kRbCUo789bQXY' OR c.name = 'Union Comedy')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'crowdwork'
  );

-- ---- Stand Up Stick Up Comedy Club (Eventbrite) ----
INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Stand Up Stick Up Comedy Club', '25 Exchange St', 'https://standupstickup.com/',
    'Lynn', 'MA', '01901', 'America/New_York', 'US', 'club',
    'ChIJUUgljfdt44kRa8FsoQp-RDs', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJUUgljfdt44kRa8FsoQp-RDs'
       OR name = 'Stand Up Stick Up Comedy Club'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/59005476163',
    '59005476163',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJUUgljfdt44kRa8FsoQp-RDs' OR c.name = 'Stand Up Stick Up Comedy Club')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
