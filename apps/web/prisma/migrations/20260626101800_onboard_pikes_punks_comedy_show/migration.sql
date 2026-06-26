-- Onboard Pikes Punks Comedy Show (Colorado Springs, CO) — TASK-3438, objective discover-comedy-venues near 80202.
--
-- Pikes Punks Comedy Show is an independent monthly stand-up showcase (touring
-- headliners + local comics) curated by Russell Keller. It runs primarily at
-- The Public House at The Alexander (3104 N Nevada Ave, Colorado Springs) on the
-- last Saturday of the month, but is a roving producer that occasionally pops up
-- at other venues (COATI in Downtown COS, Brues Alehouse in Pueblo). Tickets are
-- sold through the Eventbrite organizer `pikes-punks-comedy-show-35273577653`
-- (pikespunkscomedy.eventbrite.com).
--
-- It is wired to the generic `eventbrite` scraper in ORGANIZER mode (source_url
-- contains `/o/`), which groups events by venue and upserts a per-venue club for
-- each, so the synthetic organizer club is hidden (visible=false) and shows
-- surface under the real per-venue clubs (e.g. "The Public House at The
-- Alexander"). Verified: 1 show scraped (Pikes Punks Comedy Show: Billy Anderson).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Synthetic (hidden) organizer club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Pikes Punks Comedy Show',
       '3104 N Nevada Ave, Colorado Springs, CO 80907, USA',
       'https://www.eventbrite.com/o/pikes-punks-comedy-show-35273577653',
       'Colorado Springs', 'CO', '80907', 'America/Denver', 'US', 'club',
       'ChIJKTnueNK9cYkRBolLyz3zyyU', false, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Pikes Punks Comedy Show');

-- 2. Eventbrite organizer-mode scraping source (no unique constraint beyond PK,
--    so guard with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite',
       'https://www.eventbrite.com/o/pikes-punks-comedy-show-35273577653', '35273577653', 0, true, '{}'
FROM clubs c
WHERE c.name = 'Pikes Punks Comedy Show'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  );
