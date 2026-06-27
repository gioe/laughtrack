-- Onboard Coral Springs Center for the Arts (Coral Springs, FL) — TASK-3356,
-- objective #11 discover-comedy-venues near Miami 33130 / Fort Lauderdale 33301.
--
-- Multi-genre performing-arts theater (mostly music/tribute/variety) that also
-- books touring stand-up/improv comics. Its ticketing backend (AudienceView
-- eVenue, thecenter.evenue.net) is bot-walled, but the venue's OWN site
-- (thecentercs.com) exposes a server-rendered, category-filtered comedy listing
-- at /events/category/comedy plus per-event /events/detail/<slug> pages.
--
-- Datasource: the venue's own comedy listing, wired to the NEW `coral_springs_center`
-- venue scraper (built in this task, TASK-3356). The scraper discovers the comedy
-- detail URLs from the server-filtered listing (no keyword heuristic needed — the
-- CMS filters comedy server-side) and parses each detail page (m-date month/day/year
-- spans + h1.title + showtime + eVenue buy link) into shows whose show_page_url
-- points at the venue's own detail page. platform='custom' (venue-specific scraper).
--
-- Fixed venue (its own theater) -> visible=true.
--
-- Verified: `make scrape-club-id ID=<club_id>` scraped 1 comedy show
-- (Colin Mochrie and Brad Sherwood: Asking For Trouble, 2026-10-09 7:30PM ET);
-- the comedy slate is currently sparse but the venue programs touring comics
-- recurringly, so future comedy auto-surfaces through the same filter.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. The fixed venue club (visible). Guard on name OR google_place_id.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Coral Springs Center for the Arts',
       '2855 Coral Springs Dr',
       'https://www.thecentercs.com',
       'Coral Springs', 'FL', '33065',
       'America/New_York', 'US', 'club',
       'ChIJXYwBfEUF2YgR0frxW7sjecw',
       true, 'active'
WHERE NOT EXISTS (
  SELECT 1 FROM clubs
  WHERE name = 'Coral Springs Center for the Arts'
     OR google_place_id = 'ChIJXYwBfEUF2YgR0frxW7sjecw'
);

-- 2. The coral_springs_center scraping source. platform='custom' (venue-specific
-- scraper); source_url is the venue's server-rendered comedy-category listing.
-- Locate the club by name OR google_place_id for idempotency parity with the guard.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'coral_springs_center',
       'https://www.thecentercs.com/events/category/comedy',
       0, true, '{}'::jsonb
FROM clubs c
WHERE (c.name = 'Coral Springs Center for the Arts' OR c.google_place_id = 'ChIJXYwBfEUF2YgR0frxW7sjecw')
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources s
    WHERE s.club_id = c.id AND s.scraper_key = 'coral_springs_center'
  );
