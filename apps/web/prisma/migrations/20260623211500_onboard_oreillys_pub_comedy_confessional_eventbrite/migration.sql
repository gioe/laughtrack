-- Onboard O'Reilly's Pub / "Comedy Confessional" (San Francisco, CA) via the
-- existing eventbrite scraper - TASK-3215.
--
-- O'Reilly's Pub (1840 Haight St) hosts a recurring stand-up show, "Comedy
-- Confessional" ("Come spill your funniest secrets and embarrassing moments...
-- where laughter is the best therapy"), ticketed through Eventbrite organizer
-- 103664741931 (138 events / 2,411 attendees on record at onboarding time). The
-- discovery hit named the show ("Comedy Confessional") but the physical venue is
-- O'Reilly's Pub, so the club is onboarded under the VENUE identity.
--
-- The generic `eventbrite` scraper runs in organizer mode (source_url is a `/o/`
-- feed): it groups the organizer's events by Eventbrite venue and attaches each
-- show to the matching per-venue club. The Eventbrite venue name is
-- "O'Reilly's Pub" in (San Francisco, CA), so naming this club to match lets the
-- organizer scraper's exact/normalized name resolver attach the O'Reilly's Pub
-- comedy shows here. Any other venue in the organizer feed auto-creates its own
-- per-venue club from the same feed.
--
-- Fixed venue (the pub is its own venue) -> visible = TRUE. No title filter: the
-- organizer is the show's own producer, not a mixed-use venue feed.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'O''Reilly''s Pub', '1840 Haight St, San Francisco, CA 94117, USA',
    'https://www.eventbrite.com/o/103664741931',
    'San Francisco', 'CA', '94117', 'America/Los_Angeles', 'US', 'club',
    'ChIJZR11JweHhYAR-Cn6-V0SDaU', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJZR11JweHhYAR-Cn6-V0SDaU'
       OR name = 'O''Reilly''s Pub'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/103664741931',
    '103664741931',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJZR11JweHhYAR-Cn6-V0SDaU' OR c.name = 'O''Reilly''s Pub')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
