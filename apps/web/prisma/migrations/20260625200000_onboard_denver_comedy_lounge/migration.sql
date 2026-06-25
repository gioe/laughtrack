-- Onboard Denver Comedy Lounge (Denver, CO) — TASK-3398
-- (discover-comedy-venues near 80202).
--
-- Denver Comedy Lounge is an intimate stand-up room + sake bar in the RiNo Arts
-- District. It runs a custom Next.js site (Vercel + Sanity CMS) and sells every
-- show via on-site Stripe checkout — there is no ticketing-platform feed
-- (Eventbrite is used only for the occasional guest event). The venue-owned
-- /shows page server-renders a schema.org ItemList of upcoming shows; each item
-- carries a title plus a detail URL whose slug encodes the date and start time
-- (e.g. /shows/friday-7pm-2026-06-26). A dedicated venue scraper
-- (scraper_key = 'denver_comedy_lounge') parses that ItemList and derives the
-- datetime from each slug. Verified: 62 shows scraped (Fri/Sat weekly stand-up,
-- Jun 26 - Sep 19 2026).
--
-- Idempotent: guarded with NOT EXISTS so it no-ops where rows already exist and
-- reproduces the onboarding on a fresh database.

-- 1. Fixed (visible) venue club.
INSERT INTO clubs (name, address, website, city, state, zip_code, timezone, country, club_type, google_place_id, latitude, longitude, visible, status)
SELECT 'Denver Comedy Lounge',
       '3559 Larimer St, Denver, CO 80205, USA',
       'https://denvercomedylounge.com',
       'Denver', 'CO', '80205', 'America/Denver', 'US', 'club',
       'ChIJgae_mhx5bIcRF_lLFXrT_jA', 39.7637, -104.9812, true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM clubs WHERE name = 'Denver Comedy Lounge');

-- 2. Dedicated venue scraping source (no unique constraint beyond PK, so guard
--    with NOT EXISTS on (club_id, scraper_key)). source_url = the venue-owned
--    /shows ItemList listing page; the scraper needs no extra metadata.
INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, priority, enabled, metadata)
SELECT c.id, 'custom', 'denver_comedy_lounge',
       'https://denvercomedylounge.com/shows', 0, true, '{}'::jsonb
FROM clubs c
WHERE c.name = 'Denver Comedy Lounge'
  AND NOT EXISTS (
    SELECT 1 FROM scraping_sources ss
    WHERE ss.club_id = c.id AND ss.scraper_key = 'denver_comedy_lounge'
  );
