-- TASK-695: Generalize Tixr scraper — migrate haha_comedy_club to generic 'tixr' scraper key
-- The haha_comedy_club scraper is functionally identical to the new generic tixr scraper.

UPDATE clubs
SET scraper = 'tixr'
WHERE scraper = 'haha_comedy_club';

-- After deploying, verify the row was updated (prisma migrate deploy exits 0 even on 0-row updates):
-- SELECT COUNT(*) FROM clubs WHERE scraper = 'haha_comedy_club';  -- should be 0
-- SELECT id, name, scraper FROM clubs WHERE name ILIKE '%haha%';  -- should show scraper = 'tixr'
