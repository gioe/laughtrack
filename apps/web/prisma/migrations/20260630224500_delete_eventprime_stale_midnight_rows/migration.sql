-- TASK-3547: remove stale Flip Flops EventPrime rows created before the
-- scraper enriched midnight feed rows from detail-page em_start_time metadata.
--
-- A patched manual scrape on 2026-06-30 produced 43 upcoming shows with
-- 0 residual local-midnight EventPrime events. The old 00:00 rows no longer
-- match the corrected show datetimes, so normal stale reconciliation tried to
-- delete 13 future shows but hit the safety cap. Delete only those obsolete
-- future local-midnight rows for this venue/source shape; child tickets,
-- tagged_shows, and lineup_items cascade from shows.

DELETE FROM shows
WHERE club_id = 10978
  AND date >= CURRENT_DATE
  AND show_page_url LIKE 'https://flipflopscomedy.com/all-events/?event=%'
  AND EXTRACT(HOUR FROM date AT TIME ZONE 'America/New_York') = 0
  AND EXTRACT(MINUTE FROM date AT TIME ZONE 'America/New_York') = 0;
