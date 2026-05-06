-- TASK-1951: Fix duplicate SeatEngine external_id 487 — The Well Comedy Club
-- (club 77) and Wicked Funny Comedy Club North Andover (club 82) both pointed
-- at SeatEngine venue 487. Direct probe of services.seatengine.com/api/v1/
-- venues/487 returns "Wicked Funny Comedy Club North Andover", confirming
-- club 82 was correctly mapped and club 77's external_id was wrong.
--
-- The Well's actual SeatEngine venue ID is 502, confirmed two ways:
--   1. thewellcomedyclub.com/events footer: "Powered by SeatEngine"; the
--      header logo links to https://venue-the-well-comedy-club-502.seatengine.cloud/.
--   2. GET /api/v1/venues/502 returns
--      {name: "The Well Comedy Club", website: "https://www.thewellcomedyclub.com/"}.
--
-- The seatengine_classic scraper used by club 77 doesn't consume external_id
-- (it scrapes source_url HTML directly), so the wrong ID hadn't broken
-- nightly runs — but audit/disposition scripts (e.g. the no-events probe in
-- disposition_seatengine_no_events_2026_05_05.py) hit
-- /api/v1/venues/<external_id>/shows and were silently reading Wicked Funny's
-- 0-show response for The Well, masking The Well's real status. Keep
-- scraper_key='seatengine_classic' — only fix the venue ID.

UPDATE scraping_sources
   SET external_id = '502'
 WHERE id = 182
   AND club_id = 77
   AND platform = 'seatengine'
   AND external_id = '487';
