-- Onboard Improv Playhouse Theater via Eventbrite venue mode — TASK-2974
--
-- Improv Playhouse Theater (130 N Milwaukee Ave, Libertyville, IL) lists shows
-- on its own site as Eventbrite event links. Organizer "Improv Playhouse"
-- (organizer_id 2174468471) also runs a non-comedy patriotic chorus
-- ("Voices of Liberty"), so organizer mode over-captures. Eventbrite VENUE mode
-- (venue_id 297979971) returns only the comedy programming ("Improv Comedy
-- Shows") and attaches it directly to this cleanly-named visible club, so we use
-- venue mode here (source_url has no /o/, eventbrite_id = venue id).
--
-- Verified: real scrape returned 1 comedy show attached to this club.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Improv Playhouse Theater', '130 N Milwaukee Ave, Libertyville, IL 60048', 'http://www.improvplayhouse.com/', 'Libertyville', 'IL', '60048', 'America/Chicago', 'US', 'club', 'ChIJgXDMosmWD4gRSMC9DDhKGyQ', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Improv Playhouse Theater');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'http://www.improvplayhouse.com/', '297979971', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Improv Playhouse Theater'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
