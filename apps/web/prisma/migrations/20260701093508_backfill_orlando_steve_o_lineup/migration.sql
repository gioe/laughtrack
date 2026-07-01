-- Backfill Orlando Funny Bone's existing Steve-O rows after broadening the
-- shared show-title comedian matcher to allow known one-token punctuated names.
--
-- These Etix rows were already scraped, but had no lineup_items because the
-- previous matcher excluded "Steve-O" before it could match the show title.

INSERT INTO lineup_items (show_id, comedian_id)
SELECT s.id, c.uuid
  FROM shows s
  JOIN clubs cl ON cl.id = s.club_id
  JOIN comedians c ON lower(c.name) = lower('Steve-O')
 WHERE cl.id = 1027
   AND lower(cl.name) = lower('Orlando Funny Bone')
   AND s.name = 'STEVE-O: THE CRASH & BURN TOUR'
   AND s.show_page_url = 'https://orlando.funnybone.com/events/category/series/steve-o-the-crash-burn-tour-2/orlando-funny-bone'
ON CONFLICT (show_id, comedian_id) DO NOTHING;
