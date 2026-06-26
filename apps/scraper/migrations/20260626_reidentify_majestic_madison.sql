-- TASK-3468: Re-identify corrupted club 2953 from Dallas TX to its true
-- Madison WI Majestic identity (also resolves a Dallas duplicate with club 5001).
--
-- Surfaced by the TASK-3460 source_venue_geo_mismatch audit. Club 2953
-- 'Majestic Theatre' carried a Dallas, TX identity (name/address/city/state/
-- lat-lng/google_place_id from a TASK-3027-style Google Places mis-enrichment —
-- the generic name matched the Dallas Majestic), but its enabled ticketmaster
-- source (ticketmaster_id KovZpZAaltvA, scraper_key live_nation) is the Majestic
-- Theatre in Madison, WI, and its single ingested show is a Madison event
-- (show_page_url ticketmaster.com/phoebe-robinson-...-madison-wisconsin-...).
-- The row was already internally inconsistent: its zip_code was 53703 (a Madison
-- zip) while every other field said Dallas.
--
-- Critically, club 2953's Dallas identity was a literal DUPLICATE of the real
-- 'Majestic Theatre Dallas' (club 5001): both carried the identical
-- google_place_id ChIJ7a3r1yGZToYRdUsgLzgV_MY and Dallas lat/lng. Re-identifying
-- 2953 to its true Madison venue therefore both fixes the geo corruption AND
-- removes the Dallas duplicate, leaving 5001 as the sole, correct Dallas
-- Majestic. No existing Madison Majestic club row exists, so this is
-- collision-free (same audited re-identify pattern as TASK-3363 / TASK-3467).
--
-- Canonical Madison Majestic identity (verified 2026-06-26):
--   - Ticketmaster Discovery venue KovZpZAaltvA: Majestic Theatre, 115 King St.,
--     Madison, WI 53703, lat 43.074566 / lng -89.380978, timezone
--     America/Chicago.
--   - Google Places id ChIJ--unuD9TBogRafgJ5a1n53A (find_place_id on the name +
--     full Madison address), replacing the Dallas id ChIJ7a3r1yGZToYRdUsgLzgV_MY.
-- Name is disambiguated to 'Majestic Theatre - Madison' to match the
-- city-suffixed naming of the sibling Majestic rows (Dallas 5001, San Antonio
-- 4737). Timezone is unchanged (both cities are America/Chicago). The
-- ticketmaster source and the single show are left as-is (correctly Madison).
--
-- NOTE: the clubs table has no updated_at column (unlike scraping_sources), so
-- this UPDATE intentionally omits it (TASK-3467 incident / convention #244).
--
-- Idempotent: the guard matches only while the row still carries the Dallas
-- google_place_id, so a re-run is a no-op.

UPDATE clubs
   SET name = 'Majestic Theatre - Madison',
       address = '115 King St, Madison, WI 53703, USA',
       city = 'Madison',
       state = 'WI',
       zip_code = '53703',
       timezone = 'America/Chicago',
       latitude = 43.074566,
       longitude = -89.380978,
       google_place_id = 'ChIJ--unuD9TBogRafgJ5a1n53A'
 WHERE id = 2953
   AND google_place_id = 'ChIJ7a3r1yGZToYRdUsgLzgV_MY';
