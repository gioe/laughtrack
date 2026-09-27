-- TASK-4058: evidence-reviewed identity links and inherited suppression.
-- Keep every comedian UUID and dependent favorite/lineup/podcast row.
-- Sara/Sarah and Just Nesh are deliberately not modified. Handle equality
-- alone is not sufficient evidence for a merge. See the accompanying audit.
BEGIN;
SET LOCAL TIME ZONE 'UTC';
CREATE TABLE IF NOT EXISTS comedian_identity_repairs_4058 (
    comedian_id integer PRIMARY KEY,
    before_state jsonb NOT NULL,
    after_state jsonb NOT NULL,
    repaired_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS comedian_observation_repairs_4058 (
    observation_id bigint PRIMARY KEY,
    original_row jsonb NOT NULL
);
-- No archive FKs: deleting a source record later must not erase the audit.
DO $repair$
DECLARE
    item jsonb;
    guard jsonb;
    current_state jsonb;
    old_state jsonb;
    new_state jsonb;
    archived comedian_identity_repairs_4058%ROWTYPE;
    observation_count integer;
BEGIN
    -- Lock parents and children together before validating lineage.
    PERFORM 1 FROM comedians WHERE id IN (162399,180157,166992,712,207621,14618,1488180,226475,171846,908,746,54369,440843,535810,1068549,223894,549605,312265) ORDER BY id FOR UPDATE;
    FOR guard IN SELECT value FROM jsonb_array_elements('[{"id": 180157, "uuid": "84be107555ab31e700ea40b27549fb3f", "name": "Aidan Bishop", "parent_comedian_id": null, "visible": true, "instagram_account": "aidobishop"}, {"id": 712, "uuid": "84835facb19d09ae8c9858081a02bb6f", "name": "Joyelle Nicole Johnson", "parent_comedian_id": null, "visible": true, "instagram_account": "joyellenicole"}, {"id": 14618, "uuid": "c1c24a8837bedbbedf90298f979e66ca", "name": "Jenny Saldaña", "parent_comedian_id": null, "visible": true, "instagram_account": "littlebrowngirlshow"}, {"id": 226475, "uuid": "5debc975dfb81fc879ef2039f1323d79", "name": "Marcus D. Wiley", "parent_comedian_id": null, "visible": true, "instagram_account": "marcusdwiley"}, {"id": 908, "uuid": "b4e3873aadf93f5e2916efdf4b8ae9fe", "name": "Zach McGovern", "parent_comedian_id": null, "visible": true, "instagram_account": "zachmcgovern"}, {"id": 54369, "uuid": "446d2e87934a7db2ba51b2ba6fbfa588", "name": "Just Nesh", "parent_comedian_id": null, "visible": true, "instagram_account": "justnesh"}, {"id": 223894, "uuid": "612feab1556a87ba24f2ab980af854aa", "name": "Cory and Chad", "parent_comedian_id": null, "visible": false, "instagram_account": null, "block_reason": "not a comic", "block_added_by": "cmpvpqpmn0002jo0570rhgix9", "block_added_at": "2026-06-05T12:49:09.989463+00:00"}, {"id": 549605, "uuid": "4496192f2de8b3bba5598c43cd6f9441", "name": "Jane Don''t", "parent_comedian_id": null, "visible": false, "instagram_account": null, "block_reason": "not a comic", "block_added_by": "cmqa68z4x0002i9041l14qtcf", "block_added_at": "2026-08-19T13:55:28.852483+00:00"}, {"id": 312265, "uuid": "c303bf4200ba3078714cd029032dc003", "name": "Therapy Gecko", "parent_comedian_id": null, "visible": false, "instagram_account": null, "block_reason": "manual_removal", "block_added_by": "remove_comedians_script", "block_added_at": "2026-04-04T19:50:40.950435+00:00"}]'::jsonb) LOOP
        IF NOT EXISTS (SELECT 1 FROM comedians c WHERE c.id=(guard->>'id')::integer
                       AND to_jsonb(c) @> guard) THEN
            RAISE EXCEPTION 'TASK-4058: canonical/blocked parent guard changed for %', guard->>'id';
        END IF;
    END LOOP;
    FOR item IN SELECT value FROM jsonb_array_elements('[{"id": 162399, "before": {"id": 162399, "uuid": "0e84d72f8c102c0051f9fd9f284b9fcc", "name": "Aiden Bishop", "parent_comedian_id": null, "visible": true, "instagram_account": "aidobishop", "instagram_followers": 2681, "instagram_followers_refreshed_at": "2026-07-24T09:00:18.712083+00:00", "popularity": 0.1388, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"parent_comedian_id": 180157}}, {"id": 166992, "before": {"id": 166992, "uuid": "ea5234938e2632c298cab9378d87c800", "name": "Joyelle Johnson", "parent_comedian_id": null, "visible": true, "instagram_account": "joyellenicole", "instagram_followers": 43000, "instagram_followers_refreshed_at": "2026-07-25T08:53:54.703504+00:00", "popularity": 0.216, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"parent_comedian_id": 712}}, {"id": 207621, "before": {"id": 207621, "uuid": "01fc3fddfc01e13c345f7da67dfa3b7a", "name": "Jenny Saldana", "parent_comedian_id": null, "visible": true, "instagram_account": "littlebrowngirlshow", "instagram_followers": 3072, "instagram_followers_refreshed_at": "2026-07-25T08:49:53.818235+00:00", "popularity": 0.1998, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"parent_comedian_id": 14618}}, {"id": 1488180, "before": {"id": 1488180, "uuid": "ea5ac6ed07798d2b18fa0e220a1a8f75", "name": "Marcus Wiley", "parent_comedian_id": null, "visible": true, "instagram_account": "marcusdwiley", "instagram_followers": 118000, "instagram_followers_refreshed_at": "2026-08-05T13:16:42.539+00:00", "popularity": 0.416, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"parent_comedian_id": 226475}}, {"id": 171846, "before": {"id": 171846, "uuid": "894e082251c914651c46be80e5b11ba3", "name": "Zack McGovern", "parent_comedian_id": null, "visible": true, "instagram_account": "zachmcgovern", "instagram_followers": 20699, "instagram_followers_refreshed_at": "2026-07-03T20:16:52.899227+00:00", "popularity": 0.1772, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"parent_comedian_id": 908}}, {"id": 746, "before": {"id": 746, "uuid": "44a9fc969bd1a5eea2132f3ed366163d", "name": "Julie Lim", "parent_comedian_id": null, "visible": true, "instagram_account": "justnesh", "instagram_followers": 247000, "instagram_followers_refreshed_at": "2026-07-25T08:53:54.703504+00:00", "popularity": 0.0099, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"instagram_account": null, "instagram_followers": null, "instagram_followers_refreshed_at": null, "popularity": 0}}, {"id": 440843, "before": {"id": 440843, "uuid": "7c9f20c773222759068554dac0918729", "name": "Cory and Chad - The Smash Brothers", "parent_comedian_id": 223894, "visible": true, "instagram_account": null, "instagram_followers": null, "instagram_followers_refreshed_at": null, "popularity": 0.144, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"visible": false, "popularity": 0, "block_reason": "reviewed_alias_of_blocked_identity", "block_added_by": "TASK-4058"}}, {"id": 535810, "before": {"id": 535810, "uuid": "ef35941a3acc05a46cf84b4c5ef2ef7c", "name": "Jane Don''t Does America", "parent_comedian_id": 549605, "visible": true, "instagram_account": null, "instagram_followers": null, "instagram_followers_refreshed_at": null, "popularity": 0.0756, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"visible": false, "popularity": 0, "block_reason": "reviewed_alias_of_blocked_identity", "block_added_by": "TASK-4058"}}, {"id": 1068549, "before": {"id": 1068549, "uuid": "88fb887986d118070a05ceda7372a13c", "name": "Therapy Gecko Live", "parent_comedian_id": 312265, "visible": true, "instagram_account": null, "instagram_followers": null, "instagram_followers_refreshed_at": null, "popularity": 0.1188, "block_reason": null, "block_added_by": null, "block_added_at": null}, "patch": {"visible": false, "popularity": 0, "block_reason": "reviewed_alias_of_blocked_identity", "block_added_by": "TASK-4058"}}]'::jsonb) LOOP
        SELECT jsonb_build_object('id', c.id, 'uuid', c.uuid, 'name', c.name, 'parent_comedian_id', c.parent_comedian_id, 'visible', c.visible, 'instagram_account', c.instagram_account, 'instagram_followers', c.instagram_followers, 'instagram_followers_refreshed_at', c.instagram_followers_refreshed_at, 'popularity', c.popularity, 'block_reason', c.block_reason, 'block_added_by', c.block_added_by, 'block_added_at', c.block_added_at) INTO current_state
        FROM comedians c WHERE c.id=(item->>'id')::integer;
        SELECT * INTO archived FROM comedian_identity_repairs_4058
        WHERE comedian_id=(item->>'id')::integer;
        IF FOUND THEN
            IF current_state IS DISTINCT FROM archived.after_state THEN
                RAISE EXCEPTION 'TASK-4058: previously repaired identity % has changed', item->>'id';
            END IF;
            CONTINUE; -- Never overwrite the original backup or reapply a rollback.
        END IF;
        IF current_state IS DISTINCT FROM item->'before' THEN
            RAISE EXCEPTION 'TASK-4058: expected identity state changed for %', item->>'id';
        END IF;
        old_state := current_state;
        new_state := old_state || (item->'patch');
        IF (item->>'id')::integer IN (440843,535810,1068549) THEN
            new_state := new_state || jsonb_build_object('block_added_at', CURRENT_TIMESTAMP);
        END IF;
        IF (item->>'id')::integer = 746 THEN
            -- Zero popularity is justified only while no other signal exists.
            IF EXISTS (SELECT 1 FROM comedians c WHERE id=746 AND
                (total_shows<>0 OR sold_out_shows<>0 OR coalesce(tiktok_followers,0)<>0 OR coalesce(youtube_followers,0)<>0))
                OR EXISTS (SELECT 1 FROM lineup_items WHERE comedian_id=old_state->>'uuid')
                OR EXISTS (SELECT 1 FROM favorite_comedians WHERE comedian_id=old_state->>'uuid')
                OR EXISTS (SELECT 1 FROM comedian_podcasts WHERE comedian_id=746 AND review_status='accepted')
                OR EXISTS (SELECT 1 FROM episode_appearances WHERE comedian_id=746 AND review_status='accepted') THEN
                RAISE EXCEPTION 'TASK-4058: Julie Lim acquired another popularity signal; re-evaluate';
            END IF;
            PERFORM 1 FROM comedian_follower_observations
            WHERE comedian_id=746 AND platform::text='instagram' FOR UPDATE;
            SELECT count(*) INTO observation_count FROM comedian_follower_observations
            WHERE comedian_id=746 AND platform::text='instagram';
            IF observation_count<>1 OR NOT EXISTS (
                SELECT 1 FROM comedian_follower_observations
                WHERE id=693 AND comedian_id=746 AND platform::text='instagram'
                  AND follower_count=247000
                  AND observed_at='2026-07-25T00:00:00Z'::timestamptz
                  AND created_at='2026-07-25T08:53:54.703504Z'::timestamptz
            ) THEN
                RAISE EXCEPTION 'TASK-4058: Julie Lim Instagram observation cohort changed';
            END IF;
            INSERT INTO comedian_observation_repairs_4058 (observation_id, original_row)
            SELECT id,to_jsonb(o) FROM comedian_follower_observations o
            WHERE id=693;
            DELETE FROM comedian_follower_observations WHERE id=693;
        END IF;
        INSERT INTO comedian_identity_repairs_4058 (comedian_id,before_state,after_state,repaired_at)
        VALUES ((item->>'id')::integer,old_state,new_state,CURRENT_TIMESTAMP);
        UPDATE comedians c SET
            parent_comedian_id=(new_state->>'parent_comedian_id')::integer,
            visible=(new_state->>'visible')::boolean,
            instagram_account=new_state->>'instagram_account',
            instagram_followers=(new_state->>'instagram_followers')::integer,
            instagram_followers_refreshed_at=(new_state->>'instagram_followers_refreshed_at')::timestamptz,
            popularity=(new_state->>'popularity')::double precision,
            block_reason=new_state->>'block_reason',
            block_added_by=new_state->>'block_added_by',
            block_added_at=(new_state->>'block_added_at')::timestamptz
        WHERE c.id=(item->>'id')::integer;
        SELECT jsonb_build_object('id', c.id, 'uuid', c.uuid, 'name', c.name, 'parent_comedian_id', c.parent_comedian_id, 'visible', c.visible, 'instagram_account', c.instagram_account, 'instagram_followers', c.instagram_followers, 'instagram_followers_refreshed_at', c.instagram_followers_refreshed_at, 'popularity', c.popularity, 'block_reason', c.block_reason, 'block_added_by', c.block_added_by, 'block_added_at', c.block_added_at) INTO current_state
        FROM comedians c WHERE c.id=(item->>'id')::integer;
        IF current_state IS DISTINCT FROM new_state THEN
            RAISE EXCEPTION 'TASK-4058: identity postcondition failed for %', item->>'id';
        END IF;
    END LOOP;
    IF (SELECT count(*) FROM comedian_identity_repairs_4058)<>9
       OR (SELECT count(*) FROM comedian_observation_repairs_4058)<>1
       OR EXISTS (SELECT 1 FROM comedian_follower_observations WHERE comedian_id=746 AND platform::text='instagram') THEN
        RAISE EXCEPTION 'TASK-4058: repair archive/observation postcondition failed';
    END IF;
END $repair$;
COMMIT;

-- Guarded rollback: copy the following block and execute explicitly.
-- It refuses any post-repair edits instead of overwriting them. The archives
-- remain immutable after rollback; reapplication intentionally refuses.
/*
BEGIN;
SET LOCAL TIME ZONE 'UTC';
DO $rollback$
DECLARE
    archived comedian_identity_repairs_4058%ROWTYPE;
    current_state jsonb;
    old_state jsonb;
BEGIN
    IF (SELECT count(*) FROM comedian_identity_repairs_4058)<>9
       OR (SELECT count(*) FROM comedian_observation_repairs_4058)<>1 THEN
        RAISE EXCEPTION 'TASK-4058: incomplete rollback archive';
    END IF;
    PERFORM 1 FROM comedians WHERE id IN (SELECT comedian_id FROM comedian_identity_repairs_4058)
    ORDER BY id FOR UPDATE;
    FOR archived IN SELECT * FROM comedian_identity_repairs_4058 ORDER BY comedian_id LOOP
        SELECT jsonb_build_object('id', c.id, 'uuid', c.uuid, 'name', c.name, 'parent_comedian_id', c.parent_comedian_id, 'visible', c.visible, 'instagram_account', c.instagram_account, 'instagram_followers', c.instagram_followers, 'instagram_followers_refreshed_at', c.instagram_followers_refreshed_at, 'popularity', c.popularity, 'block_reason', c.block_reason, 'block_added_by', c.block_added_by, 'block_added_at', c.block_added_at) INTO current_state FROM comedians c WHERE c.id=archived.comedian_id;
        IF current_state IS DISTINCT FROM archived.after_state THEN
            RAISE EXCEPTION 'TASK-4058: rollback would overwrite later edits for %', archived.comedian_id;
        END IF;
        old_state:=archived.before_state;
        UPDATE comedians SET
            parent_comedian_id=(old_state->>'parent_comedian_id')::integer,
            visible=(old_state->>'visible')::boolean,
            instagram_account=old_state->>'instagram_account',
            instagram_followers=(old_state->>'instagram_followers')::integer,
            instagram_followers_refreshed_at=(old_state->>'instagram_followers_refreshed_at')::timestamptz,
            popularity=(old_state->>'popularity')::double precision,
            block_reason=old_state->>'block_reason',
            block_added_by=old_state->>'block_added_by',
            block_added_at=(old_state->>'block_added_at')::timestamptz
        WHERE id=archived.comedian_id;
    END LOOP;
    IF EXISTS (SELECT 1 FROM comedian_follower_observations WHERE comedian_id=746 AND platform::text='instagram') THEN
        RAISE EXCEPTION 'TASK-4058: later Julie Lim observations prevent rollback';
    END IF;
    -- Existing ID or natural-key conflicts deliberately abort this transaction.
    INSERT INTO comedian_follower_observations
    SELECT (jsonb_populate_record(NULL::comedian_follower_observations, original_row)).*
    FROM comedian_observation_repairs_4058;
END $rollback$;
COMMIT;
*/
