-- Onboard Clayton Club Saloon (Clayton, CA) via the existing eventbrite scraper - TASK-3192.
--
-- The Clayton Club Saloon (a bar) hosts a recurring "Clayton Club Comedy Night"
-- produced by Pat Pending Productions, ticketed through Pat Pending's Eventbrite
-- organizer (18996087273). Pat Pending is a roving producer (Clayton Club, True
-- Symmetry, Batch & Brine, William Welch Wines, Bottom of the Fifth, ...), so this
-- wires the venue to the generic `eventbrite` scraper in organizer mode: it groups
-- the organizer's events by Eventbrite venue and attaches each show to the matching
-- per-venue club. The "Clayton Club Saloon" venue name matches this club, so its
-- Comedy-Night shows attach here; Pat Pending's other venues auto-create their own
-- per-venue clubs from the same feed.
--
-- NOTE (verified 2026-06-23): the organizer feed scrapes cleanly (1 upcoming show),
-- but the only currently-listed Pat Pending event is at True Symmetry, not the
-- Clayton Club — the Clayton Club Comedy Night is recurring but sparse (Oct 2024,
-- Jul 2025) and the next one is not yet on sale. This club's shows will populate via
-- the venue-name match when the next night is listed (TASK-3192 criterion 10389
-- deferred for that timing-gap verification).

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'Clayton Club Saloon', '6096 Main St, Clayton, CA 94517, USA',
    'https://www.claytonclubsaloon.com/',
    'Clayton', 'CA', '94517', 'America/Los_Angeles', 'US', 'club',
    'ChIJTaE1jxJfhYARg9hn-4zfBUI', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJTaE1jxJfhYARg9hn-4zfBUI'
       OR name = 'Clayton Club Saloon'
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url, eventbrite_id,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'eventbrite'::"ScrapingPlatform",
    'eventbrite',
    'https://www.eventbrite.com/o/pat-pending-productions-18996087273',
    '18996087273',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJTaE1jxJfhYARg9hn-4zfBUI' OR c.name = 'Clayton Club Saloon')
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'eventbrite'
  );
