-- Backfill Marion Theatre's existing Steve-O shows after broadening the shared
-- show-title comedian matcher to allow known one-token punctuated names.
--
-- Root cause: LineupHandler's title matcher previously required at least two
-- whitespace-separated name words, so the already-scraped PatronTicket rows for
-- "Steve-O: Crash & Burn" existed under Marion Theatre but had no lineup_items.

INSERT INTO lineup_items (show_id, comedian_id)
SELECT s.id, c.uuid
  FROM shows s
  JOIN clubs cl ON cl.id = s.club_id
  JOIN comedians c ON lower(c.name) = lower('Steve-O')
 WHERE cl.id = 3289
   AND lower(cl.name) = lower('Marion Theatre')
   AND s.name = 'Steve-O: Crash & Burn'
   AND s.show_page_url IN (
       'https://reillyartscenter.my.salesforce-sites.com/ticket/#/instances/a0FV1000002lkmDMAQ',
       'https://reillyartscenter.my.salesforce-sites.com/ticket/#/instances/a0FV10000036artMAA'
   )
ON CONFLICT (show_id, comedian_id) DO NOTHING;
