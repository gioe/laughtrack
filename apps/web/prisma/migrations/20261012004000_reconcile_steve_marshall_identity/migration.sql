-- TASK-4169: retain the reviewed alternate identity as an alias, with a
-- durable before-image so the parent link and removed lineup rows can be undone.
CREATE TABLE IF NOT EXISTS task4169_comedian_identity_backup (
    comedian_id INTEGER PRIMARY KEY,
    before_state JSONB NOT NULL,
    lineup_rows JSONB NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $repair$
DECLARE
    child comedians%ROWTYPE;
    canonical comedians%ROWTYPE;
    removed_count INTEGER;
BEGIN
    SELECT * INTO canonical FROM comedians WHERE id = 126599 FOR UPDATE;
    SELECT * INTO child FROM comedians WHERE id = 1923778 FOR UPDATE;
    -- Empty/development databases need not contain this production identity.
    IF child.id IS NULL THEN RETURN; END IF;
    IF canonical.id IS NULL
       OR canonical.name <> 'Steve Marshall'
       OR canonical.uuid <> '3234af5d3e597793e5ceaf56b6a86706'
       OR canonical.parent_comedian_id IS NOT NULL
       OR NOT canonical.visible
       OR child.name <> 'Steve Marshall Comedy'
       OR child.uuid <> '5f5ecba78d035f743a1a7bbf5cd61bda'
       OR NOT child.visible THEN
        RAISE EXCEPTION 'TASK-4169 identity preconditions changed';
    END IF;
    IF EXISTS (SELECT 1 FROM task4169_comedian_identity_backup WHERE comedian_id = child.id) THEN
        IF child.parent_comedian_id IS DISTINCT FROM canonical.id THEN
            RAISE EXCEPTION 'TASK-4169 previously repaired alias has changed';
        END IF;
        RETURN;
    END IF;
    IF child.parent_comedian_id IS NOT NULL THEN
        RAISE EXCEPTION 'TASK-4169 child already has an unexpected parent';
    END IF;
    -- Never discard a unique show association or a differing performer role.
    PERFORM 1 FROM lineup_items
    WHERE comedian_id IN (child.uuid, canonical.uuid) FOR UPDATE;
    IF EXISTS (
        SELECT 1 FROM lineup_items old
        WHERE old.comedian_id = child.uuid AND NOT EXISTS (
            SELECT 1 FROM lineup_items existing
            WHERE existing.show_id = old.show_id
              AND existing.comedian_id = canonical.uuid
              AND existing.role IS NOT DISTINCT FROM old.role
        )
    ) THEN
        RAISE EXCEPTION 'TASK-4169 child has a non-overlapping show or role';
    END IF;
    IF (SELECT count(*) FROM lineup_items WHERE comedian_id = child.uuid) <> 5 THEN
        RAISE EXCEPTION 'TASK-4169 expected five reviewed child lineup rows';
    END IF;
    INSERT INTO task4169_comedian_identity_backup (comedian_id, before_state, lineup_rows)
    SELECT child.id,
           jsonb_build_object('uuid', child.uuid, 'name', child.name,
                              'parent_comedian_id', child.parent_comedian_id,
                              'total_shows', child.total_shows,
                              'sold_out_shows', child.sold_out_shows,
                              'popularity', child.popularity),
           jsonb_agg(to_jsonb(li) ORDER BY li.show_id)
    FROM lineup_items li WHERE li.comedian_id = child.uuid;

    UPDATE comedians SET parent_comedian_id = canonical.id,
                         total_shows = 0, sold_out_shows = 0, popularity = 0
    WHERE id = child.id;
    DELETE FROM lineup_items WHERE comedian_id = child.uuid;
    GET DIAGNOSTICS removed_count = ROW_COUNT;
    IF removed_count <> 5 THEN
        RAISE EXCEPTION 'TASK-4169 removed % rows instead of five', removed_count;
    END IF;
    RAISE NOTICE 'TASK-4169 linked one alias and removed % duplicate lineup rows', removed_count;
END
$repair$;

-- Rollback (operator-reviewed transaction): restore parent_comedian_id,
-- total_shows, sold_out_shows and popularity from before_state only while the
-- row still has parent 126599 and the archived name/uuid. Reinsert lineup_rows
-- via jsonb_to_recordset (id integer, show_id integer, comedian_id text, role text),
-- guarding that shows still exist and using ON CONFLICT (show_id, comedian_id)
-- DO NOTHING. Do not delete or rewrite canonical lineup rows. Retain the archive
-- as evidence and coordinate rollback with the ingestion fix.
