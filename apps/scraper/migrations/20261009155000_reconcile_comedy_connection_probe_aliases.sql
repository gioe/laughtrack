-- TASK-4146: the first verification scrape exposed upstream truncated names.
-- Retain any attached discovery history while hiding these three task-created
-- aliases and attaching them to the verified pre-existing canonical identities.
UPDATE comedians AS c
SET parent_comedian_id = correction.parent_id, visible = FALSE
FROM (VALUES
    (2666165, 'Andre De', 485953),
    (2666192, 'One Funny', 225886),
    (2666196, 'Jerry Wayne', 265890)
) AS correction(id, name, parent_id)
WHERE c.id = correction.id AND c.name = correction.name
  AND c.created_at = TIMESTAMPTZ '2026-10-09 14:59:04.404005+00';
