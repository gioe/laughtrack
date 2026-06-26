-- TASK-3380: Document that Nashville Improv (club 196) is genuinely sparse — its
-- squarespace source is correct, not stale.
--
-- Investigation (2026-06-26): club 196 had only 1 upcoming show. Verified the
-- configured source is healthy and fully covering, NOT drifted:
--   - source_url collectionId 69af0d8e38f8403f319d32d8 is the CURRENT events
--     collection (it backs nashvilleimprov.com/shows).
--   - GetItemsByMonth on that collection returns exactly the 1 real upcoming
--     event the club has ingested: "Nashville Improv presents: Your Musical!"
--     (2026-06-27), a recurring monthly improv show posted one date at a time.
--   - The venue's /shows "Upcoming Shows" lists only that recurring musical.
--
-- TRAP avoided: the Squarespace site also exposes several *template* event
-- collections (e.g. 69af0a47512bcd432e1dfd97, 69af0d8e38f8403f319d32e9,
-- 69b84a6906d33017175ae113, 5c5a519771c10ba3470d8101) that each return ~30
-- events/month — but those are Lorem Ipsum demo content ("Cursus Amet",
-- "Pellentesque Risus Ridiculus", ...), NOT real shows. Do NOT switch the source
-- to a higher-count collection without inspecting titles first.
--
-- No source change is needed; this migration only records the verification on the
-- source metadata so future audits don't re-investigate. Idempotent: re-running
-- merges the same note keys.

UPDATE scraping_sources s
   SET metadata = COALESCE(s.metadata, '{}'::jsonb) || jsonb_build_object(
           'task_3380_verified_sparse', jsonb_build_object(
               'verified_at', '2026-06-26',
               'finding', 'Genuinely sparse: venue lists one recurring "Nashville Improv presents: YOUR Musical!" improv show, posted one date at a time. Configured collectionId 69af0d8e38f8403f319d32d8 is current and fully covering (backs /shows); 1 upcoming real event matches what is ingested.',
               'do_not_switch_collection', 'Sibling collectionIds (69af0a47512bcd432e1dfd97, 69af0d8e38f8403f319d32e9, 69b84a6906d33017175ae113, 5c5a519771c10ba3470d8101) return ~30 events/month but are Squarespace TEMPLATE Lorem Ipsum demo content, not real shows.'
           )
       ),
       updated_at = NOW()
  FROM clubs c
 WHERE s.club_id = c.id
   AND c.id = 196
   AND s.platform = 'squarespace'::"ScrapingPlatform";
