-- TASK-3043: ticketmaster_national now resolves discovered venues by the
-- stable Ticketmaster venue id in scraping_sources before falling back to name.
-- These four venues were kept on per-venue ticketmaster_comedy in TASK-3042
-- only because their existing LaughTrack club names differ from the national
-- Ticketmaster venue names. With id-first resolution, national maps them back
-- to the source-owned clubs instead of inserting duplicate clubs.

UPDATE scraping_sources
   SET enabled = FALSE, updated_at = NOW()
 WHERE scraper_key = 'ticketmaster_comedy'
   AND enabled = TRUE
   AND ticketmaster_id IN (
        'KovZpZAantEA',    -- The Blue Note - MO -> The Blue Note
        'Z7r9jZa7ef',      -- Hartford Funny Bone -> Funny Bone Comedy Club - Hartford
        'Z7r9jZa7p8',      -- Toledo Funny Bone -> Funny Bone - Toledo
        'rZ7HnEZ173A8A'    -- The Winchester Music Tavern -> The Winchester
   );

-- Earlier national probes already created two visible duplicate rows before
-- TASK-3043 re-keyed the upsert. Move any non-conflicting shows back to the
-- source-owned club, drop exact show duplicates that already exist there, then
-- hide the duplicate club rows only if they are left without state. These are
-- separate statements because PostgreSQL data-modifying CTEs share a snapshot;
-- the final club UPDATE must see the prior show cleanup.
WITH club_map(duplicate_club_id, canonical_club_id) AS (
    VALUES
        (9290, 4504),  -- Funny Bone - Toledo -> Toledo Funny Bone
        (9432, 4904)   -- Funny Bone Comedy Club - Hartford -> Hartford Funny Bone
)
DELETE FROM shows sh
 USING club_map cm
 WHERE sh.club_id = cm.duplicate_club_id
   AND EXISTS (
        SELECT 1
          FROM shows existing
         WHERE existing.club_id = cm.canonical_club_id
           AND existing.date = sh.date
           AND COALESCE(existing.room, '') = COALESCE(sh.room, '')
   );

WITH club_map(duplicate_club_id, canonical_club_id) AS (
    VALUES
        (9290, 4504),  -- Funny Bone - Toledo -> Toledo Funny Bone
        (9432, 4904)   -- Funny Bone Comedy Club - Hartford -> Hartford Funny Bone
)
UPDATE shows sh
   SET club_id = cm.canonical_club_id
  FROM club_map cm
 WHERE sh.club_id = cm.duplicate_club_id
   AND NOT EXISTS (
        SELECT 1
          FROM shows existing
         WHERE existing.club_id = cm.canonical_club_id
           AND existing.date = sh.date
           AND COALESCE(existing.room, '') = COALESCE(sh.room, '')
   );

UPDATE clubs c
   SET visible = FALSE
 WHERE c.id IN (9290, 9432)
   AND c.visible = TRUE
   AND NOT EXISTS (SELECT 1 FROM scraping_sources s WHERE s.club_id = c.id)
   AND NOT EXISTS (SELECT 1 FROM shows sh WHERE sh.club_id = c.id)
   AND NOT EXISTS (SELECT 1 FROM favorite_clubs fc WHERE fc.club_id = c.id);
