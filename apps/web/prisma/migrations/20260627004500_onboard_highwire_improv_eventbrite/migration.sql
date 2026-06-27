-- Onboard Highwire Improv (Baltimore, MD) — TASK-3336
-- (discover-comedy-venues near 21201; Google primary_type=association_or_organization
-- — it's actually a Canton improv theater).
--
-- Highwire Improv runs weekly recurring public ticketed improv shows (Chaos Hour,
-- Character Building, Friday Fun and Games, Baltimore Bodega, etc.) plus a few
-- Highwire-produced "comedy tour on a boat" dates at the Baltimore Water Taxi. Every
-- show is published on the venue's own Eventbrite organizer "Highwire Improv"
-- (id 32042122709, 50 live events).
--
-- Datasource: the venue's own Eventbrite organizer, wired to the generic `eventbrite`
-- scraper in SINGLE-VENUE mode (convention #192): source_url omits the /o/ segment and
-- eventbrite_id holds the organizer id. The organizer tags events with venue name
-- "Highwire Improv" (differs from this club's name) and a few at "Baltimore Water Taxi",
-- so organizer mode would split shows across duplicate auto-clubs (TASK-3151 caveat);
-- single-venue mode forces every show onto this one club. The /venues/{id}/events/ probe
-- for the organizer id returns 404 (not 200+empty), so the venue->organizer fallback
-- fires and the scrape lands all events (convention #252).
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 87 improv-comedy shows onto the
-- single club (no duplicate auto-club created).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Highwire Improv',
       '400 S Conkling St, Baltimore, MD 21224',
       'https://www.highwireimprov.com',
       'Baltimore', 'MD', '21224', 'America/New_York', 'US', 'club',
       'ChIJE-gWAXHjtkcRB5D_ul9SQpY', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Highwire Improv');

-- 2. Eventbrite single-venue source (no /o/ in source_url; eventbrite_id = organizer id).
--    Guard with NOT EXISTS on (club_id, scraper_key) — no unique constraint beyond the PK.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, eventbrite_id, priority, enabled, metadata)
SELECT c.id, 'eventbrite', 'eventbrite', 'https://www.eventbrite.com', '32042122709', 0, true,
       '{}'::jsonb
FROM clubs c
WHERE c.name = 'Highwire Improv'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'eventbrite'
  );
