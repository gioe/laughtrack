-- Remove the DUPLICATE Spaced Out Comedy onboarding created by TASK-3228.
--
-- WHY: TASK-3228 ("Onboard scraper for Spaced Out Comedy", spacedoutcomedy.com) and the
-- sibling TASK-3226 ("Have a Laugh") independently onboarded the SAME Eventbrite organizer
-- "Spaced Out Comedy" (organizer id 80647104493). spacedoutcomedy.com redirects via
-- spacedoutcomedy.eventbrite.com to that organizer's events. The two tasks raced in
-- parallel loop sessions and both shipped to main:
--
--   * TASK-3226 (commit 9299b1162, migration 20260623235600_onboard_have_a_laugh_spaced_out_eventbrite):
--     organizer-mode production_companies row id=32, website/scraping_url =
--     https://www.eventbrite.com/o/spaced-out-comedy-80647104493. CANONICAL - merged first. KEPT.
--
--   * TASK-3228 (commit 19c8a99c3, migration 20260623230000_onboard_spaced_out_comedy_eventbrite,
--     merged via PR #32 / 52df85aa7): single-venue-mode clubs row "Spaced Out Comedy"
--     (id 11131) + scraping_sources id 6900 (eventbrite_id=298215115, the Mystérieux Brand
--     Eventbrite venue). DUPLICATE - both feeds resolve to the same organizer 80647104493
--     and would double-scrape / double-attribute the same shows on every nightly run.
--
-- ACTION: Per the cross-session dedupe directive, remove TASK-3228's duplicate club +
-- scraping_source (and the single show currently attached to club 11131) so only TASK-3226's
-- organizer-mode production_company id=32 remains. Idempotent: each DELETE is a no-op if the
-- rows were already removed.
--
-- NOTE: club 11131 is identified by its Google place_id (ChIJ08q2uW7Nj4ARhRQpV2EzRvY); the
-- TASK-3226 production_company has NO clubs row, so this cannot accidentally remove the
-- canonical onboarding.

-- 1) Detach/remove shows that were attributed to the duplicate single-venue club. These shows
--    will be re-scraped under the canonical organizer (TASK-3226 id=32) on the next nightly run.
DELETE FROM shows
WHERE club_id IN (
    SELECT id FROM clubs WHERE google_place_id = 'ChIJ08q2uW7Nj4ARhRQpV2EzRvY'
);

-- 2) Remove the duplicate scraping_sources row (single-venue eventbrite_id 298215115).
DELETE FROM scraping_sources
WHERE eventbrite_id = '298215115'
  AND club_id IN (
      SELECT id FROM clubs WHERE google_place_id = 'ChIJ08q2uW7Nj4ARhRQpV2EzRvY'
  );

-- 3) Remove the duplicate clubs row.
DELETE FROM clubs
WHERE google_place_id = 'ChIJ08q2uW7Nj4ARhRQpV2EzRvY';
