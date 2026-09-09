-- TASK-3984: remove the one confirmed lineup attribution created when the
-- Eventbrite title fallback split a cancellation-decorated event title, and
-- ensure both known cancellation-title identities remain suppressed.
--
-- Production snapshot (2026-09-08):
--   * comedians.id=1956121 ("**Cancelled** Sureni") owns lineup_items.id=420108
--     on show 3858273. The same show already owns the correct canonical Sureni
--     Weerasekera attribution at lineup_items.id=387791.
--   * comedians.id=1611038 ("**Cancelled** Nico Carney") is already hidden and
--     owns no lineup rows.
--   * Both artifact rows were hidden through the admin before this migration;
--     their existing block_reason/block_added_by/block_added_at values must be
--     preserved for auditability.
--
-- Rollback (run only after re-verifying the same show and comedian identities):
--
-- INSERT INTO lineup_items (id, show_id, comedian_id, role)
-- VALUES (420108, 3858273, 'cdf8bc8dd04a40723a16328e329c6576', NULL)
-- ON CONFLICT (show_id, comedian_id) DO NOTHING;
--
-- Do not unhide either artifact during rollback: both visibility blocks
-- predated this migration and carry independently recorded admin audit data.

DO $$
DECLARE
    deleted_lineup_count integer;
    suppressed_identity_count integer;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 15
          AND uuid = '0cc3cf7952250ec55241ffb0667df02d'
          AND name = 'Sureni Weerasekera'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3984: canonical Sureni Weerasekera row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 1956121
          AND uuid = 'cdf8bc8dd04a40723a16328e329c6576'
          AND name = '**Cancelled** Sureni'
          AND parent_comedian_id IS NULL
    ) THEN
        RAISE EXCEPTION 'TASK-3984: Cancelled Sureni artifact row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 1611038
          AND uuid = 'bf137258662d2dfc1468d4d60427fc20'
          AND name = '**Cancelled** Nico Carney'
          AND parent_comedian_id IS NULL
    ) THEN
        RAISE EXCEPTION 'TASK-3984: Cancelled Nico Carney artifact row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM shows
        WHERE id = 3858273
          AND name = '**Cancelled** Sureni & Lovers *new date announced*'
          AND date = TIMESTAMPTZ '2026-08-22 23:30:00+00'
          AND club_id = 9
          AND show_page_url = 'https://www.eventbrite.com/e/cancelled-sureni-lovers-new-date-announced-tickets-1993564140008'
    ) THEN
        RAISE EXCEPTION 'TASK-3984: audited Eventbrite show is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM lineup_items
        WHERE id = 387791
          AND show_id = 3858273
          AND comedian_id = '0cc3cf7952250ec55241ffb0667df02d'
          AND role IS NULL
    ) THEN
        RAISE EXCEPTION 'TASK-3984: canonical Sureni attribution is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM lineup_items
        WHERE comedian_id = 'cdf8bc8dd04a40723a16328e329c6576'
          AND NOT (
              id = 420108
              AND show_id = 3858273
              AND role IS NULL
          )
    ) THEN
        RAISE EXCEPTION 'TASK-3984: Cancelled Sureni owns an unexpected lineup row';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM lineup_items
        WHERE comedian_id = 'bf137258662d2dfc1468d4d60427fc20'
    ) THEN
        RAISE EXCEPTION 'TASK-3984: Cancelled Nico Carney unexpectedly owns a lineup row';
    END IF;

    DELETE FROM lineup_items
    WHERE id = 420108
      AND show_id = 3858273
      AND comedian_id = 'cdf8bc8dd04a40723a16328e329c6576'
      AND role IS NULL;

    GET DIAGNOSTICS deleted_lineup_count = ROW_COUNT;

    IF deleted_lineup_count NOT IN (0, 1) THEN
        RAISE EXCEPTION 'TASK-3984: expected to delete at most one lineup row, deleted %', deleted_lineup_count;
    END IF;

    UPDATE comedians
    SET visible = false
    WHERE (id = 1956121
           AND uuid = 'cdf8bc8dd04a40723a16328e329c6576'
           AND name = '**Cancelled** Sureni'
           AND parent_comedian_id IS NULL)
       OR (id = 1611038
           AND uuid = 'bf137258662d2dfc1468d4d60427fc20'
           AND name = '**Cancelled** Nico Carney'
           AND parent_comedian_id IS NULL);

    GET DIAGNOSTICS suppressed_identity_count = ROW_COUNT;

    IF suppressed_identity_count <> 2 THEN
        RAISE EXCEPTION 'TASK-3984: expected to suppress 2 artifact identities, updated %', suppressed_identity_count;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM lineup_items
        WHERE comedian_id IN (
            'cdf8bc8dd04a40723a16328e329c6576',
            'bf137258662d2dfc1468d4d60427fc20'
        )
    ) THEN
        RAISE EXCEPTION 'TASK-3984: an artifact lineup attribution remains after repair';
    END IF;

    IF (
        SELECT count(*)
        FROM comedians
        WHERE id IN (1956121, 1611038)
          AND visible = false
          AND parent_comedian_id IS NULL
    ) <> 2 THEN
        RAISE EXCEPTION 'TASK-3984: artifact identities were not both suppressed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM lineup_items
        WHERE id = 387791
          AND show_id = 3858273
          AND comedian_id = '0cc3cf7952250ec55241ffb0667df02d'
          AND role IS NULL
    ) THEN
        RAISE EXCEPTION 'TASK-3984: canonical Sureni attribution changed during repair';
    END IF;
END $$;
