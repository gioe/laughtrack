-- Onboard Butler Street Derby (Pittsburgh, PA) — TASK-2910
--
-- Butler Street Derby (4203 Butler St, Lawrenceville) is a bar/restaurant/event
-- venue whose own site (butlerstreetderby.com) carries NO public show calendar —
-- its /events/ page is private-booking only. Comedy is published exclusively via
-- the venue's own Eventbrite organizer ("Butler Street Derby", 104793337181):
-- a recurring "Comedy Spectacular" stand-up series (1st Jan 2025 → 5th Mar 2026,
-- roughly every 2-3 months) plus "BSD: COMEDY SHOW". Eventbrite is therefore the
-- genuine datasource (the club's own site does not hydrate listings).
--
-- scraper_key=eventbrite (existing generic scraper). ORGANIZER mode (source_url
-- contains /o/, eventbrite_id = organizer id): the venue-events endpoint
-- (/venues/296330036) returns 0 for this foreign venue, but the organizer feed
-- (/organizers/104793337181) returns the comedy events. The organizer's only
-- venue is Butler Street Derby itself, so the organizer pipeline resolves back
-- to THIS club (exact name + location match) rather than creating a per-venue
-- proxy — hence a fixed venue, visible=TRUE. Verified: 1 show scraped
-- ("BSD: COMEDY SHOW", 2026-07-16).
--
-- Idempotent: NOT EXISTS-guarded INSERTs; no-ops where rows already exist.

INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Butler Street Derby', '4203 Butler St, Pittsburgh, PA 15201', 'https://butlerstreetderby.com', 'Pittsburgh', 'PA', '15201', 'America/New_York', 'US', 'club', 'ChIJJYk8XXLzNIgRIZF7xOchKXs', TRUE, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Butler Street Derby');

INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata, created_at, updated_at)
SELECT c.id, 'eventbrite'::"ScrapingPlatform", 'eventbrite', 'https://www.eventbrite.com/o/butler-street-derby-104793337181', '104793337181', 0, TRUE, '{}'::jsonb, now(), now()
FROM clubs c WHERE c.name = 'Butler Street Derby'
  AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite');
