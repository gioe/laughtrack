-- TASK-3975: remove three confirmed false-positive alias lineup attributions
-- without unlinking the legitimate Erik B -> Erik Bransteen and
-- Ismo -> Ismo Leikola identities.
--
-- Production audit snapshot (2026-08-21):
--   * Erik B had 67 lineup rows. Shows 292687 and 338059 explicitly credit
--     Erik Bergstrom and already contain his canonical lineup row, so only the
--     redundant Erik B rows are removed. The other 65 rows remain attributed
--     to the valid Erik B alias.
--   * Ismo had 26 lineup rows. Show 1179312 is Carlos Vior's Spanish monologue;
--     "mismo" produced a substring collision with Ismo. The other 25 rows all
--     have titles that explicitly identify ISMO and remain attributed to the
--     valid Ismo alias. Reassign the contaminated row to Carlos Vior so the
--     show keeps its legitimate performer attribution.
--
-- Rollback (run transactionally after verifying the guarded current state):
--
-- UPDATE lineup_items
-- SET comedian_id = 'bbcd01f7880ecab12b0e640470489980'
-- WHERE id = 130518
--   AND show_id = 1179312
--   AND comedian_id = '5a4b3fb3d54b3f761c7b546815df63c3'
--   AND role IS NULL;
--
-- INSERT INTO lineup_items (id, show_id, comedian_id, role)
-- VALUES
--   (69175, 292687, 'bcef90a680ff397860d24bb8eefd78d0', NULL),
--   (76909, 338059, 'bcef90a680ff397860d24bb8eefd78d0', NULL)
-- ON CONFLICT (show_id, comedian_id) DO NOTHING;
--
-- The Carlos Vior identity is intentionally safe to retain on rollback. Remove
-- it only if it is still the exact pristine TASK-3975-created row and has no
-- lineup or other dependent records; never cascade-delete later enrichment.

DO $$
DECLARE
    deleted_erik_count integer;
    reassigned_ismo_count integer;
BEGIN
    -- Fail closed if any audited identity has changed since the production
    -- snapshot. The parent assertions are repeated after the lineup repair.
    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 23896
          AND uuid = 'a9788362c7e0d59acb380fd23dad10bc'
          AND name = 'Erik Bransteen'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3975: canonical Erik Bransteen row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 126571
          AND uuid = 'bcef90a680ff397860d24bb8eefd78d0'
          AND name = 'Erik B'
          AND parent_comedian_id = 23896
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3975: Erik B alias row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 13896
          AND uuid = '1320916cb03374395b27e6c96cb7ccea'
          AND name = 'Erik Bergstrom'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3975: canonical Erik Bergstrom row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 1699406
          AND uuid = 'a0b0adbd61cdfdf2b11fbaa0b26660e7'
          AND name = 'Ismo Leikola'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3975: canonical Ismo Leikola row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 234998
          AND uuid = 'bbcd01f7880ecab12b0e640470489980'
          AND name = 'Ismo'
          AND parent_comedian_id = 1699406
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3975: Ismo alias row is missing or changed';
    END IF;

    -- A name collision with a non-deterministic UUID would create two public
    -- Carlos Vior identities. Abort instead of silently introducing one.
    IF EXISTS (
        SELECT 1
        FROM comedians
        WHERE lower(name) = lower('Carlos Vior')
          AND uuid <> '5a4b3fb3d54b3f761c7b546815df63c3'
    ) THEN
        RAISE EXCEPTION 'TASK-3975: Carlos Vior already exists with an unexpected UUID';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM comedians
        WHERE uuid = '5a4b3fb3d54b3f761c7b546815df63c3'
          AND (
              name <> 'Carlos Vior'
              OR parent_comedian_id IS NOT NULL
              OR visible <> true
          )
    ) THEN
        RAISE EXCEPTION 'TASK-3975: deterministic Carlos Vior UUID is already used by a changed identity';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM comedian_deny_list
        WHERE lower(name) = lower('Carlos Vior')
    ) THEN
        RAISE EXCEPTION 'TASK-3975: Carlos Vior is deny-listed; audit before creating a canonical row';
    END IF;

    -- Pin all three show identities so stale IDs cannot mutate unrelated rows.
    IF NOT EXISTS (
        SELECT 1
        FROM shows
        WHERE id = 292687
          AND name = 'Nore Davis, Sam Jay, Gray West, Erik Bergstrom, Troy Bond, Miss Lissa Knows'
          AND date = TIMESTAMPTZ '2025-05-25 00:00:00+00'
          AND club_id = 8
          AND show_page_url = 'https://www.westsidecomedyclub.com/events/nore-davis-sam-jay-gray-west-erik-bergstrom-troy-bond-miss-lissa-knows'
    ) THEN
        RAISE EXCEPTION 'TASK-3975: audited West Side Erik Bergstrom show is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM shows
        WHERE id = 338059
          AND name = 'Nice Try ft: Jamie Wolf, Mike Cannon, Ashley Austin Morris, Adam Ferrara, Erik Bergstrom Jenny Zigrino, Brittany Carney, Gastor Almonte'
          AND date = TIMESTAMPTZ '2026-03-18 00:00:00+00'
          AND club_id = 2
          AND show_page_url = 'https://newyorkcomedyclub.com/events/nice-try-ft-jamie-wolf-mike-cannon-ashley-austin-morris-adam-ferrara-erik-bergstrom-jenny-zigrino-brittany-carney-gastor-almonte'
    ) THEN
        RAISE EXCEPTION 'TASK-3975: audited Nice Try Erik Bergstrom show is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM shows
        WHERE id = 1179312
          AND name = 'Carlos Vior - Todo mal al mismo tiempo'
          AND date = TIMESTAMPTZ '2026-04-24 18:00:00+00'
          AND club_id = 1061
          AND show_page_url = 'https://fienta.com/carlos-vior-todo-mal-al-mismo-tiempo'
    ) THEN
        RAISE EXCEPTION 'TASK-3975: audited Carlos Vior show is missing or changed';
    END IF;

    IF (
        SELECT count(*)
        FROM lineup_items
        WHERE (id = 69175
               AND show_id = 292687
               AND comedian_id = 'bcef90a680ff397860d24bb8eefd78d0'
               AND role IS NULL)
           OR (id = 76909
               AND show_id = 338059
               AND comedian_id = 'bcef90a680ff397860d24bb8eefd78d0'
               AND role IS NULL)
           OR (id = 130518
               AND show_id = 1179312
               AND comedian_id = 'bbcd01f7880ecab12b0e640470489980'
               AND role IS NULL)
    ) <> 3 THEN
        RAISE EXCEPTION 'TASK-3975: expected three exact contaminated lineup rows';
    END IF;

    IF (
        SELECT count(*)
        FROM lineup_items
        WHERE (id = 69173
               AND show_id = 292687
               AND comedian_id = '1320916cb03374395b27e6c96cb7ccea')
           OR (id = 76905
               AND show_id = 338059
               AND comedian_id = '1320916cb03374395b27e6c96cb7ccea')
    ) <> 2 THEN
        RAISE EXCEPTION 'TASK-3975: canonical Erik Bergstrom attribution is missing or changed';
    END IF;

    INSERT INTO comedians (name, uuid, visible)
    VALUES ('Carlos Vior', '5a4b3fb3d54b3f761c7b546815df63c3', true)
    ON CONFLICT (uuid) DO NOTHING;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE uuid = '5a4b3fb3d54b3f761c7b546815df63c3'
          AND name = 'Carlos Vior'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3975: canonical Carlos Vior row was not created as expected';
    END IF;

    DELETE FROM lineup_items
    WHERE (id = 69175
           AND show_id = 292687
           AND comedian_id = 'bcef90a680ff397860d24bb8eefd78d0'
           AND role IS NULL)
       OR (id = 76909
           AND show_id = 338059
           AND comedian_id = 'bcef90a680ff397860d24bb8eefd78d0'
           AND role IS NULL);

    GET DIAGNOSTICS deleted_erik_count = ROW_COUNT;

    IF deleted_erik_count <> 2 THEN
        RAISE EXCEPTION 'TASK-3975: expected to delete 2 Erik B rows, deleted %', deleted_erik_count;
    END IF;

    UPDATE lineup_items
    SET comedian_id = '5a4b3fb3d54b3f761c7b546815df63c3'
    WHERE id = 130518
      AND show_id = 1179312
      AND comedian_id = 'bbcd01f7880ecab12b0e640470489980'
      AND role IS NULL;

    GET DIAGNOSTICS reassigned_ismo_count = ROW_COUNT;

    IF reassigned_ismo_count <> 1 THEN
        RAISE EXCEPTION 'TASK-3975: expected to reassign 1 Ismo row, reassigned %', reassigned_ismo_count;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM lineup_items
        WHERE (show_id IN (292687, 338059)
               AND comedian_id = 'bcef90a680ff397860d24bb8eefd78d0')
           OR (show_id = 1179312
               AND comedian_id = 'bbcd01f7880ecab12b0e640470489980')
    ) THEN
        RAISE EXCEPTION 'TASK-3975: a contaminated alias attribution remains after repair';
    END IF;

    IF (
        SELECT count(*)
        FROM lineup_items
        WHERE show_id IN (292687, 338059)
          AND comedian_id = '1320916cb03374395b27e6c96cb7ccea'
    ) <> 2 THEN
        RAISE EXCEPTION 'TASK-3975: Erik Bergstrom attribution was lost during repair';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM lineup_items
        WHERE id = 130518
          AND show_id = 1179312
          AND comedian_id = '5a4b3fb3d54b3f761c7b546815df63c3'
          AND role IS NULL
    ) THEN
        RAISE EXCEPTION 'TASK-3975: Carlos Vior attribution was not preserved';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 126571
          AND parent_comedian_id = 23896
          AND visible = true
    ) OR NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 234998
          AND parent_comedian_id = 1699406
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3975: a legitimate alias relationship changed during repair';
    END IF;
END $$;
