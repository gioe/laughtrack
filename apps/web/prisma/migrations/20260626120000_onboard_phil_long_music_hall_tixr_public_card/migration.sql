-- Onboard Phil Long Music Hall at Bourbon Brothers (Colorado Springs, CO) —
-- TASK-3429 (discover-comedy-venues near 80202).
--
-- Phil Long Music Hall is a fixed live-music venue (13071 Bass Pro Dr, Colorado
-- Springs) — "the premier concert and live music event venue in Colorado
-- Springs". Its own Webflow site (phillongmusichall.com) renders each upcoming
-- show on /calendar as a `div.day-card` whose buy button links to a Tixr event
-- (tixr.com/e/{id}). Each card already exposes title (`.b-show`), an absolute
-- (year-bearing) date + time (`.event-info_dates p.b-venue.date`), and an
-- optional `Featuring:` performer, so Tixr is only the checkout provider and the
-- venue is wired to the generic `tixr_public_card` scraper — it parses the
-- venue-owned cards directly and never fetches DataDome-sensitive Tixr detail
-- pages.
--
-- MIXED-USE: the calendar is mostly concerts / tribute bands with only an
-- occasional stand-up night (e.g. "Comedy Night with Don McMillan",
-- "Zach Rushing"). The venue is NOT Ticketmaster-ticketed, so
-- ticketmaster_national does not cover it. The opt-in `include_title_patterns`
-- comedy allowlist (TASK-3429, TixrScraper._apply_title_filter) keeps only the
-- stand-up shows so the concerts do not pollute the comedy catalog.
--
-- The `.day-card` / `.b-show` Webflow card template is new (distinct from the
-- St. Marks / Black Buzzard / The Stand public-card variants); it is handled by
-- the TixrScraper._parse_b_show_public_cards branch shipped in the same change.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'Phil Long Music Hall at Bourbon Brothers',
       '13071 Bass Pro Dr',
       'https://www.phillongmusichall.com',
       'Colorado Springs', 'CO', '80921', 'America/Denver', 'US', 'club',
       'ChIJMdoSbuBNE4cROdUOiACZkhc', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Phil Long Music Hall at Bourbon Brothers');

-- 2. tixr_public_card scraping source with the comedy allowlist (no unique
--    constraint beyond PK, so guard with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'tixr', 'tixr_public_card',
       'https://phillongmusichall.com/calendar', 0, true,
       jsonb_build_object(
         'include_title_patterns', jsonb_build_array('comedy', 'comedian', 'stand[ -]?up'),
         'tixr_source_type', 'venue_public_card',
         'detail_fetch_required', false,
         'datadome_dependent', false,
         'audited_at', '2026-06-26',
         'audit_note', 'phillongmusichall.com/calendar renders Webflow .day-card cards (title in .b-show, absolute date/time in .event-info_dates p.b-venue.date, Tixr buy link); Tixr is only the ticket provider. Mixed-use music hall (mostly concerts) — include_title_patterns allowlists the occasional stand-up night. TASK-3429.'
       )
FROM clubs c
WHERE c.name = 'Phil Long Music Hall at Bourbon Brothers'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'tixr_public_card'
  );
