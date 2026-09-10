-- TASK-3985: make Sean Fogelson the canonical root for every known
-- That One Mailman name variant. The prior admin edits left Sean as a child
-- of one decorated-name row, which made that decorated name the family root.
--
-- This changes identity topology only. Each row keeps its UUID, visibility,
-- enrichment, and dependent records (including its existing lineup_items).
--
-- Audited pre-migration topology (2026-09-10):
--   * 532716 "Sean Fogelson \"That One Mailman\"" is the root.
--   * 325467 "Sean Fogelson" is a child of 532716.
--   * 223759 "That One Mailman" is a child of 325467.
--   * 249376 "Sean Fogelson “That 1 Mailman”" is a child of 325467.
--   * 505126 "That 1 Mailman" is a child of 325467.
--
-- Guarded rollback (run transactionally after verifying the post-migration
-- topology still matches the five assertions at the end of this migration):
--
-- UPDATE comedians
-- SET parent_comedian_id = CASE id
--     WHEN 325467 THEN 532716
--     WHEN 532716 THEN NULL
--     ELSE 325467
-- END
-- WHERE id IN (223759, 249376, 325467, 505126, 532716);

DO $$
DECLARE
    updated_count integer;
BEGIN
    -- Pin every identity field involved in the repair so a stale migration
    -- cannot re-parent a reused id or overwrite a newer manual correction.
    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 223759
          AND uuid = '4e6f2560060988d1e10546825b35faa7'
          AND name = 'That One Mailman'
          AND parent_comedian_id = 325467
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3985: That One Mailman alias row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 249376
          AND uuid = 'fcb038b1df42d2b15e2ceb6b01a7d2f0'
          AND name = 'Sean Fogelson “That 1 Mailman”'
          AND parent_comedian_id = 325467
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3985: smart-quote Sean Fogelson alias row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 325467
          AND uuid = 'c51e546f9872f9bb9245264d8e8d9749'
          AND name = 'Sean Fogelson'
          AND parent_comedian_id = 532716
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3985: canonical Sean Fogelson row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 505126
          AND uuid = 'fd6daf98ad0526b6afb4c8e470a5c4fb'
          AND name = 'That 1 Mailman'
          AND parent_comedian_id = 325467
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3985: That 1 Mailman alias row is missing or changed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 532716
          AND uuid = '67ff47cc88c533e8b2326deb02bf0e04'
          AND name = 'Sean Fogelson "That One Mailman"'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) THEN
        RAISE EXCEPTION 'TASK-3985: straight-quote Sean Fogelson alias row is missing or changed';
    END IF;

    UPDATE comedians
    SET parent_comedian_id = CASE id
        WHEN 325467 THEN NULL
        ELSE 325467
    END
    WHERE id IN (223759, 249376, 325467, 505126, 532716);

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    IF updated_count <> 5 THEN
        RAISE EXCEPTION 'TASK-3985: expected to update five family rows, updated %', updated_count;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = 325467
          AND uuid = 'c51e546f9872f9bb9245264d8e8d9749'
          AND name = 'Sean Fogelson'
          AND parent_comedian_id IS NULL
          AND visible = true
    ) OR (
        SELECT count(*)
        FROM comedians
        WHERE (id = 223759
               AND uuid = '4e6f2560060988d1e10546825b35faa7'
               AND name = 'That One Mailman'
               AND parent_comedian_id = 325467
               AND visible = true)
           OR (id = 249376
               AND uuid = 'fcb038b1df42d2b15e2ceb6b01a7d2f0'
               AND name = 'Sean Fogelson “That 1 Mailman”'
               AND parent_comedian_id = 325467
               AND visible = true)
           OR (id = 505126
               AND uuid = 'fd6daf98ad0526b6afb4c8e470a5c4fb'
               AND name = 'That 1 Mailman'
               AND parent_comedian_id = 325467
               AND visible = true)
           OR (id = 532716
               AND uuid = '67ff47cc88c533e8b2326deb02bf0e04'
               AND name = 'Sean Fogelson "That One Mailman"'
               AND parent_comedian_id = 325467
               AND visible = true)
    ) <> 4 THEN
        RAISE EXCEPTION 'TASK-3985: Sean Fogelson family did not reach the expected direct-child topology';
    END IF;
END $$;
