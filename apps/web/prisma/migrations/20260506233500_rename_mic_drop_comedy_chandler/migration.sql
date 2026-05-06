-- TASK-1990: align canonical SeatEngine venue 493 with upstream name.
--
-- TASK-1984 folded duplicate SeatEngine venue 493 rows by making club 120 the
-- canonical row and hiding/disabling club 517. Club 517 still holds the
-- upstream canonical name, so move it to an archived tombstone first to avoid
-- clubs.name unique-constraint conflicts, then rename club 120.

UPDATE clubs
SET name = 'Mic Drop Comedy Chandler [archived TASK-1984]'
WHERE id = 517
  AND name = 'Mic Drop Comedy Chandler'
  AND visible = false;

UPDATE clubs
SET name = 'Mic Drop Comedy Chandler'
WHERE id = 120
  AND name = 'Mic Drop Mania'
  AND NOT EXISTS (
      SELECT 1
      FROM clubs
      WHERE id <> 120
        AND name = 'Mic Drop Comedy Chandler'
  );
