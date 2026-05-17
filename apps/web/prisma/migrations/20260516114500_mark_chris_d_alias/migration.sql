DO $$
DECLARE
    canonical_id integer;
    alias_id integer;
    updated_count integer;
BEGIN
    SELECT id
    INTO canonical_id
    FROM comedians
    WHERE id = 223890
      AND uuid = '82738771c5a501526b9cf116c4fc0e28'
      AND name = 'Chris D''Elia'
      AND parent_comedian_id IS NULL;

    IF canonical_id IS NULL THEN
        RAISE EXCEPTION 'Cannot mark Chris D alias: canonical Chris D''Elia row is missing or already an alias';
    END IF;

    SELECT id
    INTO alias_id
    FROM comedians
    WHERE id = 348237
      AND uuid = '331d80075e275e0862419db0c0944983'
      AND name = 'Chris D';

    IF alias_id IS NULL THEN
        RAISE EXCEPTION 'Cannot mark Chris D alias: alias row is missing or changed';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM comedians
        WHERE id = alias_id
          AND parent_comedian_id IS NOT NULL
          AND parent_comedian_id <> canonical_id
    ) THEN
        RAISE EXCEPTION 'Cannot mark Chris D alias: alias row already points to another parent';
    END IF;

    UPDATE comedians
    SET parent_comedian_id = canonical_id
    WHERE id = alias_id
      AND (parent_comedian_id IS NULL OR parent_comedian_id = canonical_id);

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    IF updated_count <> 1 THEN
        RAISE EXCEPTION 'Cannot mark Chris D alias: expected to update 1 row, updated %', updated_count;
    END IF;

    INSERT INTO comedian_deny_list (name, reason, added_by)
    VALUES (
        'Chris D',
        'Alias for Chris D''Elia; prevent rediscovery as a separate comedian',
        'manual_migration'
    )
    ON CONFLICT (name) DO UPDATE
    SET reason = EXCLUDED.reason,
        added_by = EXCLUDED.added_by;
END $$;
