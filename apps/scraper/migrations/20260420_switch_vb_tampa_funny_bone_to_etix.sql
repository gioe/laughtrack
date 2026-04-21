-- TASK-1675: Switch Virginia Beach (1033) and Tampa (1053) Funny Bones from
-- live_nation to etix. Both were bulk-migrated to live_nation with the rest of
-- the Funny Bone chain (chain_id=3), but both return 0 events from the TM
-- Discovery API — their TM venue records exist but have no bookings attached.
--
-- Investigation confirmed both are actively operating and booking comedy:
--   * Virginia Beach relocated to Pembroke Square (Aug 2025, larger 450-seat
--     venue). Current 2026 lineup on vb.funnybone.com includes Michael Blackson,
--     Malik B., Christopher Titus, Steve Trevino, Felipe Esparza.
--   * Tampa is the former Tampa Improv (rebranded Dec 2023). 107+ upcoming
--     events on tampa.funnybone.com incl. Ms. Pat, Ginger Billy, Randy Feltface,
--     Michael Blackson, Steph Tolev.
--
-- Both venues' official tickets sell through Etix (their sites are "Powered by
-- Rockhouse Partners, an Etix company"). The existing scraping_url values
-- already point to the correct Etix venue pages:
--   * 1033 -> https://www.etix.com/ticket/v/31602/funny-bone-comedy-club-virginia-beach
--   * 1053 -> https://www.etix.com/ticket/v/31600/funny-bone-comedy-club-tampa
-- The generic etix scraper extracts venue_id from /v/<id>/ automatically,
-- so no additional config is needed.

UPDATE clubs
SET scraper = 'etix'
WHERE id IN (1033, 1053)
  AND scraper = 'live_nation';
