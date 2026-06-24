-- Onboard BATS Improv via the existing eventbrite scraper (organizer mode) - TASK-3244.
--
-- VENUE: BATS Improv (improv.org), an established improv-comedy theater at the
-- Bayfront Theatre, Landmark Building B / 2 Marina Blvd Bldg B, Fort Mason
-- Center, San Francisco, CA 94123 (Google place_id ChIJRdUWXd6AhYARt_JK5zJos0g).
-- Its own site (https://www.improv.org/) hydrates all upcoming shows from buy
-- links to Eventbrite ("BATS Improv presents: Whodunnit", "Super Scene", "The
-- Startup", "Cave Match", "The Short Show", "Jam-a-thon", ...) — dated public
-- ticketed improv-comedy shows. COMEDY CONFIRMED.
--
-- DUPE NOTE: this task was filed after a fuzzy dupe-check mis-matched BATS to a
-- similarly-named same-run sibling. Verified DISTINCT: no pre-existing club had
-- name LIKE 'BATS%'/improv.org/place_id ChIJRdUWXd6AhYARt_JK5zJos0g, and BATS
-- Improv (Fort Mason) is a different venue from Leela Improv (TASK-3176) and
-- from the unrelated "BATSU! Chicago" / "The Bit Theater" rows.
--
-- PLATFORM: Eventbrite. All shows belong to the verified super-organizer "BATS
-- Improv Shows" (organizer id 120768857464,
-- https://www.eventbrite.com/o/bats-improv-shows-120768857464). The Eventbrite
-- single-VENUE endpoint (venue id 296698650) returns only 1 of the ~36 live
-- events for this org (most events have no venue field set), so we onboard the
-- ORGANIZER feed and let the eventbrite scraper's organizer mode route each
-- show to its own per-venue club.
--
-- ORGANIZER MODE → HIDDEN PROXY: an Eventbrite "/o/" source activates the
-- scraper's organizer pipeline, which groups events by venue.id and upserts a
-- per-venue clubs row for each (here: "BATS Bayfront Theatre" 2 Marina Blvd, and
-- a second EB venue-name spelling "BATS Improv Theatre" / Landmark Building B —
-- both the same physical Fort Mason theater under two EB venue_ids). The
-- onboarded "BATS Improv" row is therefore the hidden synthetic organizer proxy
-- (visible = FALSE); the real public shows surface under the auto-created
-- per-venue clubs (same pattern as TASK-3219 San Francisco Comedy College and
-- TASK-3222 Black Book Comedy). The per-venue clubs are created by the scraper
-- on the next run, so this migration inserts only the proxy + its source.
--
-- MIXED FEED: the organizer's feed mixes improv CLASSES / workshops
-- ("Essential Performance Games with John Remak", "TheatreSports with Rebecca
-- Stockley", ...) with the public shows, so metadata.exclude_classes = true
-- keeps the class/course/workshop listings out (the shared eventbrite scraper's
-- built-in class title patterns). Verified 2026-06-24: organizer mode produced
-- 36 shows across 2 venues with exclude_classes on; re-runs are idempotent.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'BATS Improv',
    '2 Marina Blvd, Bldg B, 3rd Floor, Fort Mason Center, San Francisco, CA 94123, USA',
    'https://www.improv.org/',
    'San Francisco', 'CA', '94123', 'America/Los_Angeles', 'US', 'club',
    'ChIJRdUWXd6AhYARt_JK5zJos0g',
    FALSE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs WHERE name = 'BATS Improv'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/bats-improv-shows-120768857464',
    '120768857464',
    TRUE,
    0,
    jsonb_build_object('exclude_classes', true),
    NOW(),
    NOW()
FROM clubs c
WHERE c.name = 'BATS Improv'
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
