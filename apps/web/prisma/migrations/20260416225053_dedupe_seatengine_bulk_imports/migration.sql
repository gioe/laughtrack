-- De-duplicate SeatEngine bulk-import clubs (TASK-1532)
--
-- Two bulk-import clubs (TASK-1492..1531) turned out to be duplicates of pre-existing
-- DB entries that serve the same physical venue / scraping URL. Consolidate by
-- closing + hiding the bulk-import record so the older, canonical record remains.
--
-- 1. Club 826 "The Comedy Club On State" (Madison WI) — duplicate of club 435
--    "Comedy on State" (same address 202 State Street, same madisoncomedy.com URL,
--    same json_ld scraper producing identical show rows).
-- 2. Club 87 "Bananas Comedy Club Renaissance Hotel" (Rutherford NJ) — same physical
--    venue as club 850 "Bananas Comedy Club" (same 801 Rutherford Ave address, same
--    bananascomedyclub.com root). #87 was already hidden; finalize by closing so it
--    cannot be re-enabled and so the seatengine_classic scrape stops.

UPDATE clubs
SET status = 'closed',
    visible = false,
    closed_at = COALESCE(closed_at, '2026-04-16T22:50:53+00:00'::timestamptz)
WHERE id = 826 AND status <> 'closed';

UPDATE clubs
SET status = 'closed',
    closed_at = COALESCE(closed_at, '2026-04-16T22:50:53+00:00'::timestamptz)
WHERE id = 87 AND status <> 'closed';
