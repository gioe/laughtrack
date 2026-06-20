-- TASK-3034: Add explicit status for legitimate pre-launch clubs.
--
-- Pre-launch venues are distinct from temporary hiatuses: they are not open
-- yet, but should still exist in the club database with verified address data.

ALTER TABLE clubs
    DROP CONSTRAINT IF EXISTS clubs_status_check;

ALTER TABLE clubs
    ADD CONSTRAINT clubs_status_check
        CHECK (status IN ('active', 'closed', 'hiatus', 'not_open_yet'));

UPDATE clubs
   SET status = 'not_open_yet'
 WHERE google_place_id = 'ChIJszI0pGvTD4gRQJJ5CYItf-k'
    OR lower(name) = lower('The Home Comedy Theater');
