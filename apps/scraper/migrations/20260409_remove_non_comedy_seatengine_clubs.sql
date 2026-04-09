-- TASK-1098: Remove 14 non-comedy SeatEngine bulk-import clubs.
--
-- These venues were bulk-imported from the SeatEngine venue directory on 2026-04-06
-- without individual research. None are comedy clubs — they include test entries,
-- individual comedian pages, production companies, festivals, charities, and
-- non-comedy event producers. All have 0 shows in the DB.
--
-- Corresponding deny-list entries added to club_quality_rules.yaml to prevent
-- re-import by the SeatEngine national scraper.

BEGIN;

-- Close and hide all 14 clubs.
UPDATE clubs
SET status  = 'closed',
    visible = false
WHERE id IN (
    807,  -- test 2
    832,  -- Events by KathySings4u
    804,  -- Fiesta De Independencia
    844,  -- FUNCHAMANIA!
    849,  -- I Am Battle Comic | Hermosa Beach Community Theater
    839,  -- Submit to the 208 Comedy Festival Please
    841,  -- Suits for Soldiers
    825,  -- Wave Entertainment
    783,  -- Mike Gardner Comedy
    827,  -- Jess Miller Comedy Shows
    791,  -- MobRun Productions
    805,  -- Don Barnhart Entertainment
    829,  -- Bridgestones Comedy Shows
    803   -- Mad Hatter Shows
);

COMMIT;
