-- Onboard Hennepin Arts (Minneapolis, MN) comedy calendar.
--
-- Hennepin Arts is a multi-theatre performing arts operator. Its public Nuxt
-- events page queries Algolia index `events_production` with `genre:Comedy`;
-- event detail pages embed exact Contentful performance `startDate` and
-- `ticketsUrl` values. Model as one operator club and store the specific
-- theatre in Show.room.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, visible, status)
SELECT 'Hennepin Arts', '900 Hennepin Ave, Minneapolis, MN 55403', 'https://hennepinarts.org', 'Minneapolis', 'MN', '55403', 'America/Chicago', 'US', 'club', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Hennepin Arts');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'custom'::"ScrapingPlatform", 'hennepin_arts',
       'https://hennepinarts.org/events?refinementList%5Bgenre%5D%5B0%5D=Comedy',
       0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c
WHERE c.name = 'Hennepin Arts'
  AND NOT EXISTS (
      SELECT 1
      FROM scraping_sources ss
      WHERE ss.club_id = c.id
        AND ss.scraper_key = 'hennepin_arts'
  );
