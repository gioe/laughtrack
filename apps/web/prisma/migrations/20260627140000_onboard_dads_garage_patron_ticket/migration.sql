-- Onboard Dad's Garage (Atlanta, GA) — TASK-3365,
-- objective #12 discover-comedy-venues near Atlanta 30303.
--
-- Major Atlanta improv-comedy theater. Its own site (dadsgarage.com) sells tickets
-- through Salesforce PatronTicket (PatronManager) at
-- dadsgarage.my.salesforce-sites.com/ticket, scraped by the existing `patron_ticket`
-- scraper. Two venue-specific wrinkles handled here:
--   1. Dad's Garage runs a newer PatronTicket package whose fetchEvents RemoteAction
--      takes 4 args (older installs use 3); the scraper was fixed in this task to
--      send the per-method arg count from the page auth config, so the wired source
--      works (the hardcoded 3-arg payload previously 400'd).
--   2. Dad's Garage tags comedy as "Improv" / "Scripted" / "Special Event" (NOT the
--      default "Comedy"), and runs multiple Salesforce venue rooms — so metadata
--      pins patronticket_venue_id to its four venue IDs and patronticket_categories
--      to the venue's comedy tokens. This keeps improv + scripted-comedy + special
--      comedy events and drops classes / camps / workshops (Class / Children's /
--      Education).
--
-- Fixed venue (its own theater) -> visible=true.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 124 comedy shows across 20
-- distinct titles (Maestro, TheatreSports, TJ and Dave, Cage Match, The Tight
-- Acquaintances, Gutenberg! The Musical!, etc.); classes/camps excluded.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Dad''s Garage',
       '569 Ezzard St SE',
       'https://www.dadsgarage.com',
       'Atlanta', 'GA', '30312',
       'America/New_York', 'US', 'club',
       'ChIJ255RQwEE9YgRSOmoPEwQbKc',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Dad''s Garage'
     OR google_place_id = 'ChIJ255RQwEE9YgRSOmoPEwQbKc'
);

-- 2. The patron_ticket scraping source. source_url is the venue's PatronTicket
-- ticket page (the scraper derives /apexremote from it). metadata pins the four
-- Salesforce venue IDs and the venue's comedy category tokens. Locate the club by
-- name OR google_place_id for idempotency parity with the guard above.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'patron_ticket', 'patron_ticket',
       'https://dadsgarage.my.salesforce-sites.com/ticket',
       0, true,
       '{"patronticket_venue_id": ["a0T4100000BCoODEA1", "a0T41000001mvXZEAY", "a0T41000001mvXaEAI", "a0T41000002wpLWEAY"], "patronticket_categories": ["Improv", "Scripted", "Special Event"]}'::jsonb
FROM clubs c
WHERE (c.name = 'Dad''s Garage' OR c.google_place_id = 'ChIJ255RQwEE9YgRSOmoPEwQbKc')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'patron_ticket'
  );
