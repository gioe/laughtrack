-- Onboard The Black Buzzard at Oskar Blues (Denver, CO) — TASK-3384, objective #13
-- (discover-comedy-venues near 80202).
--
-- The Black Buzzard is a fixed live-music + comedy venue (1624 Market St,
-- Denver). Its own Webflow homepage (theblackbuzzard.com) renders each upcoming
-- show as an `.event-item` card whose buy link points at a Tixr event
-- (tixr.com/e/{id}); each card already exposes title, an absolute (year-bearing)
-- date, time, and a per-card Schema.org JSON-LD `offers` block with the price.
-- Tixr is only the checkout provider, so the venue is wired to the generic
-- `tixr_public_card` scraper, which parses the venue-owned cards directly and
-- never fetches DataDome-sensitive Tixr detail pages.
--
-- NOTE: the venue's own homepage carries only its events; the site's `/events`
-- page is a shared "Bandwagon" Tixr group that also lists Moxi Theater (Greeley)
-- shows, so source_url intentionally points at the homepage, not /events.
--
-- This card template differs from the existing St. Marks / The Stand public-card
-- variants (different Webflow class names + absolute dates), handled by the new
-- TixrScraper._parse_buzzard_public_cards branch shipped in the same change.
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, visible, status)
SELECT 'The Black Buzzard at Oskar Blues',
       '1624 Market St',
       'https://www.theblackbuzzard.com',
       'Denver', 'CO', '80202', 'America/Denver', 'US', 'club',
       'ChIJq6qezcR4bIcR8FWsKG7l_jg', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'The Black Buzzard at Oskar Blues');

-- 2. tixr_public_card scraping source (no unique constraint beyond PK, so guard
--    with NOT EXISTS on (club_id, scraper_key)).
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'tixr', 'tixr_public_card',
       'https://www.theblackbuzzard.com/', 0, true,
       jsonb_build_object(
         'tixr_source_type', 'venue_public_card',
         'detail_fetch_required', false,
         'datadome_dependent', false,
         'audited_at', '2026-06-25',
         'audit_note', 'Webflow .event-item cards (absolute-dated variant) expose title/date/time/ticket URL + per-card JSON-LD offer price; Tixr is only the ticket provider. Homepage carries only this venue''s events (the /events page is a shared Bandwagon Tixr group with Moxi Theater). TASK-3384.'
       )
FROM clubs c
WHERE c.name = 'The Black Buzzard at Oskar Blues'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'tixr_public_card'
  );
