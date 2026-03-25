-- TASK-695: Generalize Tixr scraper — migrate haha_comedy_club to generic 'tixr' scraper key
-- The haha_comedy_club scraper is functionally identical to the new generic tixr scraper.

UPDATE clubs
SET scraper = 'tixr'
WHERE scraper = 'haha_comedy_club';
