-- Backfill the 'open-mic' Tag (id=21823) onto every Show whose name matches
-- an open-mic pattern. Closes the gap between the queryable name signal
-- (~5,133 rows at time of writing) and the previous tag coverage (292 rows
-- after the dedupe migration). Idempotent via the @@unique([show_id, tag_id])
-- constraint on tagged_shows — re-running is a no-op.
--
-- Pattern intentionally matches what humans call an open mic. It will slightly
-- over-tag showcases that brand themselves with "Open Mic" in the title even
-- when the event has a set lineup (e.g. "OPEN GYM: Comedy Open Mic ...");
-- accepted as bounded noise given the tag is visibility=ADMIN and the
-- name-pattern is also the canonical filter heuristic in code (false_positive
-- detector, lineup placeholder list, production_companies show_name_keywords).

INSERT INTO tagged_shows (show_id, tag_id)
SELECT id, 21823
FROM shows
WHERE name ILIKE '%open mic%'
   OR name ILIKE '%open-mic%'
   OR name ILIKE '%openmic%'
ON CONFLICT (show_id, tag_id) DO NOTHING;
