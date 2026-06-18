-- Onboard The Drop Comedy Club via Eventbrite organizer — TASK-2980
--
-- The Drop Comedy Club (435 S Michigan St, South Bend, IN) lists its shows on
-- its own site (thedropcomedyllc.com/events-&-ticket-links) as individual
-- Eventbrite event links. Eventbrite VENUE mode (venue_id 297616889) returned 0
-- — the organizer's events don't surface via the venue-events endpoint — so
-- ORGANIZER mode on "The Drop Comedy Club" (organizer_id 32622398403) is used.
--
-- Unlike a roving producer, this organizer runs at a single fixed venue, so the
-- anchor club is VISIBLE. Organizer mode routes each event through the per-venue
-- upsert, which fuzzy-reconciles the Eventbrite venue name
-- "The Drop Comedy Club South Bend" to this club (same normalized name +
-- city/state), so shows land back on this row rather than a duplicate.
--
-- Verified: real scrape returned 2 shows, attached to this club.
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Drop Comedy Club', '435 S Michigan St, South Bend, IN 46601', 'https://thedropcomedyllc.com/', 'South Bend', 'IN', '46601', 'America/Indiana/Indianapolis', 'US', 'club', 'ChIJORP3ZSzNFogRbiCUKCBg9cg', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Drop Comedy Club');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/32622398403', '32622398403', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'The Drop Comedy Club'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
