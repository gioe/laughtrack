-- Consolidate the kebab open-mic tag (id=21823, slug='open-mic', ADMIN,
-- name=null) onto the existing PUBLIC tag (id=1, slug='open mic', name='Open
-- Mic', user_facing=true) which is the one getFilters('show', ...) actually
-- returns and the live filter chip already uses.
--
-- Before this migration the chip surfaced only the 1,167 shows curated onto
-- id=1; the 5,148 backfilled onto id=21823 in the previous migration were
-- invisible to the UI. The slug-with-space convention is what every other
-- multi-word show tag uses on prod (live podcast, non comedy, roast battle,
-- special taping), so consolidating onto id=1 keeps the live chip's URL
-- shape unchanged and requires no client code change on either web or iOS.
--
-- After this migration:
--   - tag id=1 covers the union of both prior tag populations
--   - tag id=21823 and its rows are gone
--   - getFilters returns the same Filter row it always did (id=1, "Open Mic"),
--     and the existing ?filters=open mic URL on web + the equivalent
--     Filter.selected toggle on iOS surface the full open-mic population.

INSERT INTO tagged_shows (show_id, tag_id)
SELECT show_id, 1
FROM tagged_shows
WHERE tag_id = 21823
ON CONFLICT (show_id, tag_id) DO NOTHING;

DELETE FROM tagged_shows WHERE tag_id = 21823;
DELETE FROM tags WHERE id = 21823;
