-- Recalculate total_shows for clubs 59 and 130 after TASK-1459 show migration
UPDATE clubs
SET total_shows = (SELECT COUNT(*) FROM shows WHERE shows.club_id = clubs.id)
WHERE id IN (59, 130);
