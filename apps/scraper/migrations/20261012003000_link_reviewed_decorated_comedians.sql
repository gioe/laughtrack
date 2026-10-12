-- TASK-4170: reviewed duplicates; all archived child links already exist on the parent.
-- Before-image and transactional rollback: ../docs/audits/2026-10-12-decorated-canonicals/.
DO $repair$
DECLARE
    entry jsonb;
    child comedians%ROWTYPE;
    parent comedians%ROWTYPE;
    actual_links jsonb;
BEGIN
    -- Block concurrent lineup/identity writes while checking the archived before-image.
    LOCK TABLE comedians, lineup_items IN SHARE ROW EXCLUSIVE MODE;
    FOR entry IN SELECT value FROM jsonb_array_elements($backup$[{"child": {"id": 1123574, "uuid": "7be484f40ef52ce4f4412c6da0544d8c", "name": "Officer Eudy Comedy", "parent_comedian_id": null, "visible": true, "total_shows": 1, "sold_out_shows": 0, "popularity": 0.1709}, "parent": {"id": 663282, "uuid": "6756675d793142ef1ea80dd187707170", "name": "Officer Eudy"}, "lineups": [{"id": 244184, "show_id": 2940753, "comedian_id": "7be484f40ef52ce4f4412c6da0544d8c", "role": null}]}, {"child": {"id": 1737394, "uuid": "4c93bc789737ec17a87a94cda715d7b6", "name": "Sureni Weerasekera at The Playground!", "parent_comedian_id": null, "visible": true, "total_shows": 1, "sold_out_shows": 0, "popularity": 0.1774}, "parent": {"id": 15, "uuid": "0cc3cf7952250ec55241ffb0667df02d", "name": "Sureni Weerasekera"}, "lineups": []}, {"child": {"id": 1847300, "uuid": "83839c8aa6b07baeb09416bb340e6873", "name": "Smokey Suarez Live at Comedy In Harlem", "parent_comedian_id": null, "visible": true, "total_shows": 2, "sold_out_shows": 0, "popularity": 0.1737}, "parent": {"id": 490654, "uuid": "c94b18c37ff2e7ec565c3ec9d8be1dca", "name": "Smokey Suarez"}, "lineups": [{"id": 404887, "show_id": 5471588, "comedian_id": "83839c8aa6b07baeb09416bb340e6873", "role": null}, {"id": 428157, "show_id": 6044110, "comedian_id": "83839c8aa6b07baeb09416bb340e6873", "role": null}]}, {"child": {"id": 1923772, "uuid": "6bc01d74ceaa1e8827a797aee07a2b4c", "name": "Russ Nagel Comedy", "parent_comedian_id": null, "visible": true, "total_shows": 5, "sold_out_shows": 0, "popularity": 0.4156}, "parent": {"id": 885094, "uuid": "c11ec9b0719281382d09ffc941827170", "name": "Russ Nagel"}, "lineups": [{"id": 415279, "show_id": 5733188, "comedian_id": "6bc01d74ceaa1e8827a797aee07a2b4c", "role": null}, {"id": 415281, "show_id": 5733189, "comedian_id": "6bc01d74ceaa1e8827a797aee07a2b4c", "role": null}, {"id": 415283, "show_id": 5733190, "comedian_id": "6bc01d74ceaa1e8827a797aee07a2b4c", "role": null}, {"id": 415285, "show_id": 5733191, "comedian_id": "6bc01d74ceaa1e8827a797aee07a2b4c", "role": null}, {"id": 415287, "show_id": 5733192, "comedian_id": "6bc01d74ceaa1e8827a797aee07a2b4c", "role": null}]}, {"child": {"id": 1923790, "uuid": "dc5c989b75cb065c29c0d74bbf330716", "name": "Kris Fried Comedy", "parent_comedian_id": null, "visible": true, "total_shows": 5, "sold_out_shows": 0, "popularity": 0.4156}, "parent": {"id": 1123546, "uuid": "b471f881cf4ce5f52b5a45586d082490", "name": "Kris Fried"}, "lineups": [{"id": 415265, "show_id": 5733173, "comedian_id": "dc5c989b75cb065c29c0d74bbf330716", "role": null}, {"id": 415267, "show_id": 5733174, "comedian_id": "dc5c989b75cb065c29c0d74bbf330716", "role": null}, {"id": 415269, "show_id": 5733175, "comedian_id": "dc5c989b75cb065c29c0d74bbf330716", "role": null}, {"id": 415271, "show_id": 5733176, "comedian_id": "dc5c989b75cb065c29c0d74bbf330716", "role": null}, {"id": 415273, "show_id": 5733177, "comedian_id": "dc5c989b75cb065c29c0d74bbf330716", "role": null}]}]$backup$::jsonb)
    LOOP
        SELECT * INTO child FROM comedians WHERE id=(entry->'child'->>'id')::integer;
        IF NOT FOUND THEN CONTINUE; END IF;
        SELECT * INTO parent FROM comedians WHERE id=(entry->'parent'->>'id')::integer;
        IF NOT FOUND OR parent.uuid IS DISTINCT FROM entry->'parent'->>'uuid'
           OR parent.name IS DISTINCT FROM entry->'parent'->>'name'
           OR parent.parent_comedian_id IS NOT NULL OR parent.visible IS NOT TRUE
           OR child.uuid IS DISTINCT FROM entry->'child'->>'uuid'
           OR child.name IS DISTINCT FROM entry->'child'->>'name'
           OR child.visible IS NOT TRUE THEN
            RAISE EXCEPTION 'TASK-4170 identity changed for %', entry->'child'->>'id';
        END IF;
        SELECT COALESCE(jsonb_agg(jsonb_build_object('id',l.id,'show_id',l.show_id,
            'comedian_id',l.comedian_id,'role',l.role) ORDER BY l.show_id),'[]'::jsonb)
        INTO actual_links FROM lineup_items l WHERE l.comedian_id=child.uuid;

        -- Replay preserves later metadata edits and does not reapply the repair.
        IF child.parent_comedian_id = parent.id AND actual_links='[]'::jsonb THEN
            CONTINUE;
        END IF;
        IF child.parent_comedian_id IS NOT NULL
           OR child.total_shows IS DISTINCT FROM (entry->'child'->>'total_shows')::integer
           OR child.sold_out_shows IS DISTINCT FROM (entry->'child'->>'sold_out_shows')::integer
           OR child.popularity IS DISTINCT FROM (entry->'child'->>'popularity')::double precision
           OR actual_links IS DISTINCT FROM entry->'lineups'
           OR EXISTS (SELECT 1 FROM comedians WHERE parent_comedian_id=child.id)
           OR EXISTS (SELECT 1 FROM comedian_podcasts WHERE comedian_id=child.id)
           OR EXISTS (SELECT 1 FROM favorite_comedians WHERE comedian_id=child.uuid)
           OR EXISTS (SELECT 1 FROM episode_appearances WHERE comedian_id=child.id)
           OR EXISTS (SELECT 1 FROM lineup_items l WHERE l.comedian_id=child.uuid
               AND NOT EXISTS (SELECT 1 FROM lineup_items p WHERE p.comedian_id=parent.uuid
                   AND p.show_id=l.show_id AND p.role IS NOT DISTINCT FROM l.role)) THEN
            RAISE EXCEPTION 'TASK-4170 before-image/dependencies changed for %', child.id;
        END IF;
        DELETE FROM lineup_items WHERE comedian_id=child.uuid;
        UPDATE comedians SET parent_comedian_id=parent.id,total_shows=0,sold_out_shows=0,popularity=0
        WHERE id=child.id;
    END LOOP;
END
$repair$;
