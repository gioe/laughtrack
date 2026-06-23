-- Onboard The Stage at Burke Junction (Cameron Park, CA) via the new
-- `ticketspice` scraper - TASK-3207.
--
-- The Stage at Burke Junction (stageatburke.com; a community performing-arts
-- theater) hosts a dated, ticketed stand-up show — the "Barley & Me Pod-uctions
-- Comedy Show" — sold through a TicketSpice (Webconnex) ticketing form at
-- https://thestage.ticketspice.com/barley-me-comedy . The venue's own site is
-- Wix, but its Wix Events component carries only a non-comedy fundraiser
-- ("For the Love Dog"), so wix_events is NOT the comedy seam — the comedy show
-- lives entirely in the external TicketSpice form.
--
-- TicketSpice forms are SINGLE-EVENT ticketing pages (one form == one show on
-- one date; this one had schedules: [] and a single $9 GA level). The form HTML
-- embeds its config in a window.__BOOTSTRAP__ JS object — appSettings.formName
-- (title), appSettings.eventStart (date, no wall-clock time), and formData
-- ticket levels (price). The new generic `ticketspice` scraper
-- (scraper_key='ticketspice', platform='custom') fetches the form URL, parses
-- that bootstrap into one Show, and drops the show once its date passes (so a
-- stale un-updated form stops emitting a past show). Because the form carries no
-- show time, the Show uses metadata.default_show_time (HH:MM, default 19:00)
-- localized to the club timezone, matching the AXS homepage scraper pattern.
--
-- source_url is the TicketSpice form URL (the scraper reads it as the form to
-- fetch). visible=TRUE: a real fixed venue.
--
-- VERIFIED 2026-06-23: a live scrape of the form fetched + parsed cleanly
-- ("Barley & Me Pod-uctions Comedy Show", $9, date 2026-06-07). That single date
-- had already passed at onboarding time, so the nightly persist is 0 until the
-- venue posts their next comedy date — at which point it is picked up
-- automatically with no code change.
--
-- Idempotent: re-running reuses the club (matched by google_place_id, then
-- name+city+state) and the existing ticketspice scraping_sources row.

INSERT INTO clubs (
    name, address, website, city, state, zip_code,
    timezone, country, club_type, google_place_id, visible, status
)
SELECT
    'The Stage at Burke Junction',
    '3300 Coach Ln e1, Cameron Park, CA 95682, USA',
    'https://www.stageatburke.com/',
    'Cameron Park', 'CA', '95682', 'America/Los_Angeles', 'US', 'club',
    'ChIJkR3as_L3moAR6JI0Nlt8Tug', TRUE, 'active'
WHERE NOT EXISTS (
    SELECT 1 FROM clubs
    WHERE google_place_id = 'ChIJkR3as_L3moAR6JI0Nlt8Tug'
       OR (lower(name) = lower('The Stage at Burke Junction')
           AND lower(city) = lower('Cameron Park') AND state = 'CA')
);

INSERT INTO scraping_sources (
    club_id, platform, scraper_key, source_url,
    enabled, priority, metadata, created_at, updated_at
)
SELECT
    c.id,
    'custom'::"ScrapingPlatform",
    'ticketspice',
    'https://thestage.ticketspice.com/barley-me-comedy',
    TRUE,
    0,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM clubs c
WHERE (c.google_place_id = 'ChIJkR3as_L3moAR6JI0Nlt8Tug'
       OR (lower(c.name) = lower('The Stage at Burke Junction')
           AND lower(c.city) = lower('Cameron Park') AND c.state = 'CA'))
  AND NOT EXISTS (
      SELECT 1 FROM scraping_sources s
      WHERE s.club_id = c.id AND s.scraper_key = 'ticketspice'
  );
