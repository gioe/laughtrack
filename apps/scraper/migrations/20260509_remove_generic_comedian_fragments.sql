-- TASK-2092: Remove generic title fragments that were incorrectly persisted as comedians.
-- Delete dependent lineup rows first so this is safe even if the FK is not configured
-- with ON DELETE CASCADE in a target environment.
WITH generic_comedians AS (
    SELECT uuid
    FROM comedians
    WHERE name IN ('Music', 'More', 'Best of')
)
DELETE FROM lineup_items
WHERE comedian_id IN (SELECT uuid FROM generic_comedians);

DELETE FROM comedians
WHERE name IN ('Music', 'More', 'Best of');
