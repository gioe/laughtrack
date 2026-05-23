-- Remove stale Laugh Boston Pixl fallback tickets created before the extractor
-- stopped emitting empty-sales General Admission placeholders.
--
-- Each target show must still have a paid tier row, so the cleanup only removes
-- the obsolete zero-price fallback and leaves the real Pixl tiers intact.

CREATE TEMP TABLE _laugh_boston_stale_zero_tickets (
    show_id integer PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO _laugh_boston_stale_zero_tickets (show_id)
VALUES
    (489821),
    (489822),
    (489823),
    (489824),
    (489859),
    (489860),
    (489861),
    (489862);

DO $$
DECLARE
    stale_count integer;
BEGIN
    SELECT COUNT(*)
    INTO stale_count
    FROM _laugh_boston_stale_zero_tickets target
    JOIN shows s
      ON s.id = target.show_id
     AND s.club_id = 140
     AND s.date >= NOW()
    JOIN tickets stale
      ON stale.show_id = target.show_id
     AND stale.price = 0
     AND stale.sold_out = FALSE
     AND stale.type = 'General Admission'
    WHERE EXISTS (
        SELECT 1
        FROM tickets paid
        WHERE paid.show_id = target.show_id
          AND paid.price > 0
          AND paid.type <> 'General Admission'
    );

    IF stale_count <> 8 THEN
        RAISE EXCEPTION 'Expected 8 stale Laugh Boston zero-price fallback tickets, found %', stale_count;
    END IF;
END $$;

DELETE FROM tickets stale
USING _laugh_boston_stale_zero_tickets target, shows s
WHERE stale.show_id = target.show_id
  AND s.id = target.show_id
  AND s.club_id = 140
  AND s.date >= NOW()
  AND stale.price = 0
  AND stale.sold_out = FALSE
  AND stale.type = 'General Admission'
  AND EXISTS (
      SELECT 1
      FROM tickets paid
      WHERE paid.show_id = target.show_id
        AND paid.price > 0
        AND paid.type <> 'General Admission'
  );
