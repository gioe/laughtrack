-- TASK-3243: Onboard On the Spot Comedy (Roseville, CA), discovered via the
-- discover-comedy-venues skill. "On the Spot Improv" is a recurring, public,
-- family-friendly improv-comedy series produced by Take Note Troupe at its
-- fixed studio (Take Note Troupe Studio, 9001 Foothills Blvd., Suite 130,
-- Roseville). The studio's WordPress site runs the "The Events Calendar"
-- (Tribe) plugin, exposing a public REST API at
-- /wp-json/tribe/events/v1/events — scraped by the generic
-- `the_events_calendar` scraper.
--
-- The studio is mixed-use: the same calendar also hosts MainStage theater,
-- children's theater, and workshops (non-comedy). We therefore scope the
-- scrape to the comedy series via scraping_sources.metadata:
--   * event_categories = "on-the-spot-improv" — server-side Tribe category
--     filter, so the API only returns the comedy series.
--   * exclude_title_patterns — drops the non-show rows that share that
--     category (auditions / workshops), keeping only the public improv shows.
--
-- Fixed venue → visible=true. Idempotent (NOT EXISTS guards) so it no-ops
-- where rows already exist (prod) and reproduces state on fresh databases.


-- On the Spot Comedy (Take Note Troupe Studio) — Tribe Events / The Events Calendar
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'On the Spot Comedy', '9001 Foothills Blvd., Suite 130, Roseville, CA 95747, USA', 'https://takenotetroupe.org', 'Roseville', 'CA', '95747', 'America/Los_Angeles', 'US', 'club', 'ChIJK3rnaSEfm4ARCP0xzdQYxxY', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'On the Spot Comedy');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'tribe_events'::"ScrapingPlatform", 'the_events_calendar', 'https://takenotetroupe.org/wp-json/tribe/events/v1/events', 0, TRUE,
       '{"event_categories": "on-the-spot-improv", "exclude_title_patterns": ["Auditions", "Workshop"]}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'On the Spot Comedy'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'the_events_calendar');
