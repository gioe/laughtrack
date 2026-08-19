-- TASK-3972: repair false parent-child links that make canonical comedian
-- histories inherit unrelated shows. These child rows are retained as hidden
-- source artifacts so their lineup provenance remains auditable; only the
-- incorrect identity relationship is removed.
--
-- Audit dispositions:
--   * 348237 "Chris D" -> Chris D'Elia: unlink and keep hidden. Ten legitimate
--     Chris D'Elia appearances already have the canonical comedian in lineup_items;
--     child-only rows are ambiguous "Chris D." hosting credits or Chris Distefano.
--   * 495810 "The Neon Room at Helium: Santi Espinosa" -> Santi Espinosa:
--     unlink and hide. This is an event-series title; 175 of its 176 shows do not
--     directly credit Santi, including unrelated Neon Room headliners.
--   * 332554 "Rory" -> Rory Scovel: unlink and hide. Six legitimate Rory Scovel
--     appearances already have the canonical comedian; its child-only show is
--     explicitly Rory Gibson.
--   * 284737 "Red-Eye" -> Kedar Kelkar: unlink and hide. Red-Eye is a show-series
--     title, not a performer alias. Convert its three existing inherited show
--     attributions to direct Kedar lineup rows before suppressing the artifact.
--   * 234998 "Ismo" -> Ismo Leikola: retain; this is a legitimate short-form name.
--   * 651918 "Ry Daddy" -> Ryan Dacalos: retain; this is a legitimate stage name.
--   * 732538 "Damian Anaya along" -> Damian Anaya: retain; malformed source text,
--     but its show evidence consistently credits Damian rather than another comic.
--
-- Rollback substrate: the four child rows and their lineup_items are not deleted.
-- Restore the parent ids/previous visibility values listed in the guarded repair,
-- then remove Kedar's 421604, 421642, and 421684 lineup rows on rollback.

DO $$
DECLARE
    repaired_count integer;
    kedar_lineup_count integer;
BEGIN
    -- Fail closed if either a canonical identity or a child record has changed
    -- since the audit. This prevents a stale data repair from unlinking a reused id.
    IF NOT EXISTS (
        SELECT 1 FROM comedians
        WHERE id = 223890
          AND uuid = '82738771c5a501526b9cf116c4fc0e28'
          AND name = 'Chris D''Elia'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3972: canonical Chris D''Elia row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM comedians
        WHERE id = 1005
          AND uuid = '0d38ae63f7ce08b9a60e3fd790de8dd0'
          AND name = 'Santi Espinosa'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3972: canonical Santi Espinosa row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM comedians
        WHERE id = 23324
          AND uuid = '30fb11450e265557dc4c90b7225c4b09'
          AND name = 'Rory Scovel'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3972: canonical Rory Scovel row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM comedians
        WHERE id = 1032498
          AND uuid = 'f95a47cc9e93ff1ddba37e2ac80c1713'
          AND name = 'Kedar Kelkar'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3972: canonical Kedar Kelkar row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM comedians
        WHERE id = 348237
          AND uuid = '331d80075e275e0862419db0c0944983'
          AND name = 'Chris D'
          AND parent_comedian_id = 223890
          AND visible = false
    ) THEN
        RAISE EXCEPTION 'TASK-3972: Chris D child row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM comedians
        WHERE id = 495810
          AND uuid = '867c82efdc2ec46f6638aadc83132908'
          AND name = 'The Neon Room at Helium: Santi Espinosa'
          AND parent_comedian_id = 1005
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3972: Neon Room child row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM comedians
        WHERE id = 332554
          AND uuid = '6c27ea029ce5894cf6c66690bbe6acde'
          AND name = 'Rory'
          AND parent_comedian_id = 23324
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3972: Rory child row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM comedians
        WHERE id = 284737
          AND uuid = 'fbc01fbc1438d4c71bca7499278e89f4'
          AND name = 'Red-Eye'
          AND parent_comedian_id = 1032498
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3972: Red-Eye child row is missing or changed';
    END IF;

    IF (
        SELECT count(*)
        FROM lineup_items
        WHERE comedian_id = 'fbc01fbc1438d4c71bca7499278e89f4'
          AND show_id IN (421604, 421642, 421684)
    ) <> 3 THEN
        RAISE EXCEPTION 'TASK-3972: expected three audited Red-Eye lineup rows';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM lineup_items
        WHERE comedian_id = 'f95a47cc9e93ff1ddba37e2ac80c1713'
          AND show_id IN (421604, 421642, 421684)
    ) THEN
        RAISE EXCEPTION 'TASK-3972: canonical Kedar lineup rows already exist; audit migration state before proceeding';
    END IF;

    INSERT INTO lineup_items (show_id, comedian_id, role)
    SELECT li.show_id, 'f95a47cc9e93ff1ddba37e2ac80c1713', li.role
    FROM lineup_items li
    WHERE li.show_id IN (421604, 421642, 421684)
      AND li.comedian_id = 'fbc01fbc1438d4c71bca7499278e89f4'
    ON CONFLICT (show_id, comedian_id) DO NOTHING;

    SELECT count(*)
    INTO kedar_lineup_count
    FROM lineup_items
    WHERE show_id IN (421604, 421642, 421684)
      AND comedian_id = 'f95a47cc9e93ff1ddba37e2ac80c1713';

    IF kedar_lineup_count <> 3 THEN
        RAISE EXCEPTION 'TASK-3972: expected three canonical Kedar lineup rows, found %', kedar_lineup_count;
    END IF;

    UPDATE comedians
    SET parent_comedian_id = NULL,
        visible = false
    WHERE (id = 348237 AND parent_comedian_id = 223890 AND visible = false)
       OR (id = 495810 AND parent_comedian_id = 1005 AND visible = true)
       OR (id = 332554 AND parent_comedian_id = 23324 AND visible = true)
       OR (id = 284737 AND parent_comedian_id = 1032498 AND visible = true);

    GET DIAGNOSTICS repaired_count = ROW_COUNT;

    IF repaired_count <> 4 THEN
        RAISE EXCEPTION 'TASK-3972: expected to repair 4 child rows, repaired %', repaired_count;
    END IF;
END $$;
