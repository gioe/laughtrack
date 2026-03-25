-- TASK-693: Generalize Tockify scraper — rename scraper key from 'ice_house' to 'tockify'
-- Any existing Ice House club row is updated to use the generic 'tockify' scraper key.

UPDATE clubs
SET scraper = 'tockify'
WHERE scraper = 'ice_house';
