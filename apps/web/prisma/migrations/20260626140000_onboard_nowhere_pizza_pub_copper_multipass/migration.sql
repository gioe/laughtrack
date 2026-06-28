-- Onboard "Nowhere Pizza & Pub • Copper" (Copper Mountain / Frisco, CO) — TASK-3444
--
-- Datasource: the venue's own Wix site (nowhere-pizza.com) routes its "Nowhere
-- Stage" comedy tickets to a Multipass box office at
-- https://nowhere-copper.multipass.com/ . That server-rendered venue root lists
-- every show as a `div.eventCard2026` card (title + date/time + ticket link),
-- the exact signature consumed by the generic `multipass` scraper.
--
-- Comedy confirmed: the Multipass venue root carried 11 dated stand-up cards —
-- "Bohemian Comedy Show", "Krampus Comedy Show", "Bohemian Holiday Comedy Show"
-- ("Live on the Nowhere Stage") — verified during onboarding (TASK-3444).
--
-- Wiring: generic `multipass` scraper (no code needed), reference venue
-- "Dude, IDK Studios" (denvercomedy.multipass.com). source_url = the venue
-- Multipass subdomain root; the scraper parses all cards and filters to
-- upcoming-only. NOTE: this is a seasonal ski-resort venue — at onboarding time
-- (June 2026, off-season) all listed cards were prior-season (2025) dates, so a
-- live scrape currently yields 0 UPCOMING shows. Re-verify N>0 once the venue
-- posts its next (fall/winter) comedy lineup.
--
-- Fixed venue (the pub is its own venue), so visible=true (not a hidden
-- roving-producer proxy).
--
-- Idempotent: guarded INSERTs no-op where the club / scraping_sources row already exist.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Nowhere Pizza & Pub • Copper',
    '760 Copper Rd, Frisco, CO 80443, USA',
    'https://www.nowhere-pizza.com/',
    'Frisco', 'CO', '80443', 'America/Denver', 'US', 'club',
    'ChIJiR7Eud9faocRhuLBQhKDJ-4', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJiR7Eud9faocRhuLBQhKDJ-4'
       OR name = 'Nowhere Pizza & Pub • Copper'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'multipass',
    'https://nowhere-copper.multipass.com/',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJiR7Eud9faocRhuLBQhKDJ-4' OR c.name = 'Nowhere Pizza & Pub • Copper')
  AND NOT EXISTS (
      -- Guard on the real (club_id, platform, priority) unique constraint so a
      -- redeploy can't pass NOT EXISTS and then fail the INSERT on the
      -- constraint — a failed Prisma migration blocks all future deploys.
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id
        AND s.platform = 'custom'::"ScrapingPlatform"
        AND s.priority = 0
  );
