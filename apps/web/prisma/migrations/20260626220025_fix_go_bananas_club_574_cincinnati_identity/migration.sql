-- Correct club 574 "Go Bananas Comedy Club" identity to the Cincinnati venue — TASK-3341,
-- objective: onboard missing Cincinnati comedy venues.
--
-- Investigation (TASK-3341) found club 574 was already scraping the Cincinnati
-- Go Bananas Comedy Club at gobananascomedy.com via the existing `go_bananas`
-- scraper (125 fresh shows out to Sep 2026 — e.g. "Chad Daniels" at
-- /main/show/chad-daniels-4, matching the live Cincinnati calendar), but its
-- identity metadata was mislabeled as the Rutherford, NJ location:
--   address "801 Rutherford Ave, Rutherford, NJ 07070", city Rutherford, state NJ,
--   google_place_id ChIJpaI0oKT5wokRVTxranSpDbo.
--
-- gobananascomedy.com is unambiguously the Cincinnati (Montgomery) venue (its
-- pages carry "8410 Market Pl Ln", "Funniest Person in Cincinnati", Pro-Am
-- nights). The real Rutherford-area NJ club is a differently-named venue
-- ("Bananas Comedy Club", bananascomedyclub.com), not this site — so no NJ
-- venue is orphaned by this correction. The venue is therefore already onboarded
-- and scraped; this only fixes the wrong identity fields. No new club, no new
-- scraping_sources row, no new scraper (the `go_bananas` scraper already works).
--
-- Idempotent: keyed on the stable website + the wrong NJ state so it no-ops once
-- applied (and on any fresh DB where the row is already correct or absent).

UPDATE clubs
   SET address = '8410 Market Pl Ln, Cincinnati, OH 45242, USA',
       city = 'Cincinnati',
       state = 'OH',
       zip_code = '45242',
       google_place_id = 'ChIJebx-knBUQIgRt6MhzKt3Ds4'
 WHERE website = 'https://gobananascomedy.com'
   AND state = 'NJ';
