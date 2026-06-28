-- Onboard The Lyric (Fort Collins, CO) — TASK-3473 (re-do of TASK-3436, whose
-- in-progress scraper was lost to an orchestration error).
--
-- The Lyric (1209 N College Ave, lyriccinema.com) is an indie cinema / live-events
-- venue on the Indy Systems ticketing platform (api-*.indy.systems). Its Quasar
-- SPA talks to a same-origin GraphQL proxy at https://www.lyriccinema.com/graphql
-- where tenant + read scope are selected by request HEADERS, not the URL: the
-- net-new `the_lyric` scraper sends site-id (from metadata.indy_site_id = 7) and
-- client-type:consumer. Indy models films AND live events as "movies"; the
-- scraper keeps only comedy by event name (comedy/comedian/stand-up/improv/sketch),
-- dropping the ~220 film titles and the mixed "Open Mic" variety night.
--
-- Confirmed stand-up/improv comedy: monthly "Lyric Comedy Show" (host Luke
-- Gaston, 21+), "Comedy Night w/ The Comedy Brewers" (improv), "Fort Collins
-- Improv Fest". A live end-to-end scrape returned 4 upcoming comedy showings.
--
-- platform is the curated ScrapingPlatform enum; Indy Systems is not a member,
-- so this uses platform='custom' (like dojour) and the scraper is resolved by
-- scraper_key ('the_lyric'). Fixed venue -> visible=true.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'The Lyric',
    '1209 N College Ave, Fort Collins, CO 80524, USA',
    'https://www.lyriccinema.com',
    'Fort Collins', 'CO', '80524', 'America/Denver', 'US', 'club',
    'ChIJr0XZsfRKaYcRB0M9uhJvQ2A', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJr0XZsfRKaYcRB0M9uhJvQ2A'
       OR name = 'The Lyric'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'the_lyric',
    'https://www.lyriccinema.com/graphql',
    TRUE,
    0,
    '{"indy_site_id": 7}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJr0XZsfRKaYcRB0M9uhJvQ2A' OR c.name = 'The Lyric')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'the_lyric'
  );
