-- Dedupe open-mic Tag rows. The legacy tag id=21770 uses slug='open_mic'
-- (underscore) and is invisible to QueryHelper.getShowTagsClause, which
-- filters on the kebab slug 'open-mic' (id=21823). Re-point the 271 affected
-- taggings onto the kebab tag, then drop the orphan. Idempotent via the
-- @@unique([show_id, tag_id]) constraint on tagged_shows.

INSERT INTO tagged_shows (show_id, tag_id)
SELECT show_id, 21823
FROM tagged_shows
WHERE tag_id = 21770
ON CONFLICT (show_id, tag_id) DO NOTHING;

DELETE FROM tagged_shows WHERE tag_id = 21770;
DELETE FROM tags WHERE id = 21770;
