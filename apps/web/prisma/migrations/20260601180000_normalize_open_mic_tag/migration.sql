-- Normalize the open-mic tag onto the canonical PUBLIC row (id=1,
-- slug='open mic', name='Open Mic') and drop the two ADMIN orphans that
-- accumulated after the prior consolidation migration
-- (20260601123000_consolidate_open_mic_tag_onto_public):
--
--   id=53140, slug='open_mic'  (underscore, ADMIN, name=null) — 82 rows
--   id=53228, slug='open-mic'  (kebab,      ADMIN, name=null) — 25 rows
--
-- Pre-state was confirmed against prod via apps/scraper `make query`:
-- the canonical id=1 holds 5,172 tagged_shows rows, and the two ADMIN
-- orphans together hold 107 additional rows whose shows are not yet
-- on id=1.
--
-- The task description named only id=53228. id=53140 surfaced during
-- exploration and is handled in the same migration so the acceptance
-- criterion "exactly one Tag row matching slug ILIKE '%open%mic%'"
-- can pass — leaving id=53140 behind would re-create the ambiguity
-- the task is meant to remove.
--
-- After this migration:
--   - tag id=1 covers the union of all three prior tag populations
--   - tags id=53140 and id=53228 (and their tagged_shows rows) are gone
--   - getFilters returns the same Filter row it always did (id=1,
--     "Open Mic"); no client code change required on web or iOS.
--
-- Idempotent via the @@unique([show_id, tag_id]) constraint on
-- tagged_shows — re-running is a no-op.

INSERT INTO tagged_shows (show_id, tag_id)
SELECT show_id, 1
FROM tagged_shows
WHERE tag_id = 53140
ON CONFLICT (show_id, tag_id) DO NOTHING;

DELETE FROM tagged_shows WHERE tag_id = 53140;
DELETE FROM tags WHERE id = 53140;

INSERT INTO tagged_shows (show_id, tag_id)
SELECT show_id, 1
FROM tagged_shows
WHERE tag_id = 53228
ON CONFLICT (show_id, tag_id) DO NOTHING;

DELETE FROM tagged_shows WHERE tag_id = 53228;
DELETE FROM tags WHERE id = 53228;
