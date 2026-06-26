-- TASK-3467: Re-identify corrupted club 2861 from Wichita KS to its true
-- Minneapolis MN Orpheum identity.
--
-- Surfaced by the TASK-3460 source_venue_geo_mismatch audit. Club 2861
-- 'Orpheum Theatre' carried a Wichita, KS identity (name/address/city/state/
-- lat-lng/google_place_id from a TASK-3027-style Google Places mis-enrichment
-- — the generic name matched the Wichita Orpheum), but its enabled ticketmaster
-- source (ticketmaster_id KovZpakSUe, scraper_key live_nation) is the Orpheum
-- Theatre in Minneapolis, MN, and all 18 ingested shows are Minneapolis events
-- (show_page_url like ticketmaster.com/...-minneapolis-minnesota-...). The row
-- was already internally inconsistent: its zip_code was 55403 (a Minneapolis
-- zip) while every other field said Wichita.
--
-- Same Google-Places identity-corruption class fixed in TASK-3363 (Hard Rock
-- Live Hollywood). The shows/source are correct; only the club's identity was
-- wrong, so we re-identify the row to match its source venue (cf. TASK-3363).
-- No existing Minneapolis Orpheum club row exists, so this is collision-free.
--
-- Canonical Minneapolis Orpheum identity (verified 2026-06-26):
--   - Ticketmaster Discovery venue KovZpakSUe: Orpheum Theatre, 910 Hennepin
--     Avenue, Minneapolis, MN 55403, lat 44.976396 / lng -93.277509,
--     timezone America/Chicago.
--   - Google Places id ChIJL-FGVpEys1IR6Oz9krHwKDc (find_place_id on the name +
--     full Minneapolis address), replacing the Wichita id
--     ChIJqWXnKOrjuocRNPJmSTEr-CQ.
-- Name is disambiguated to 'Orpheum Theatre - Minneapolis' to match the
-- city-suffixed naming of the other Orpheum rows (Memphis 4626, Madison 4651,
-- Flagstaff 5382) and avoid a bare-name collision with the real Wichita Orpheum.
-- Timezone is unchanged (both cities are America/Chicago). The ticketmaster
-- source and the 18 shows are left as-is (they are correctly Minneapolis).
--
-- Idempotent: the guard matches only while the row still carries the Wichita
-- google_place_id, so a re-run is a no-op.

UPDATE clubs
   SET name = 'Orpheum Theatre - Minneapolis',
       address = '910 Hennepin Avenue, Minneapolis, MN 55403, USA',
       city = 'Minneapolis',
       state = 'MN',
       zip_code = '55403',
       timezone = 'America/Chicago',
       latitude = 44.976396,
       longitude = -93.277509,
       google_place_id = 'ChIJL-FGVpEys1IR6Oz9krHwKDc'
 WHERE id = 2861
   AND google_place_id = 'ChIJqWXnKOrjuocRNPJmSTEr-CQ';
