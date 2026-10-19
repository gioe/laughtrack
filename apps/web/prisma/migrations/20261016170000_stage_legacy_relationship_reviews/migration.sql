-- TASK-4187: explicitly authorized quarantine of unverified legacy associations.
-- Preserve complete source rows as immutable observations; never invent approval.
-- Runs before parent/host enforcement. The transaction and table locks ensure no
-- writer can observe the temporary suspension of the comedian admission trigger.
BEGIN;
SELECT curation_lock_intake();
LOCK TABLE comedians, comedian_podcasts, podcast_candidate_reviews IN ACCESS EXCLUSIVE MODE;

CREATE OR REPLACE FUNCTION pg_temp.stage_entity(entity_kind text, public_id integer) RETURNS text LANGUAGE plpgsql AS $$
DECLARE target text; public_uuid text; entity_label text; key_owner text;
BEGIN
 IF entity_kind='comedian' THEN
  SELECT id INTO target FROM curation_entities WHERE comedian_id=public_id;
  SELECT uuid,name INTO public_uuid,entity_label FROM comedians WHERE id=public_id;
  SELECT entity_id INTO key_owner FROM curation_identity_keys WHERE namespace='comedian-uuid:v1' AND scope='global' AND value=public_uuid AND curation_identity_keys.entity_kind='comedian';
  -- An observed UUID may already belong to another legacy alias. Retain its
  -- immutable key and negative policy; do not silently merge public endpoints.
  IF target IS NULL AND EXISTS(SELECT 1 FROM curation_entities WHERE id=key_owner AND (comedian_id IS NULL OR comedian_id=public_id)) THEN target:=key_owner; END IF;
  IF target IS NOT NULL THEN
   UPDATE curation_entities SET comedian_id=public_id WHERE id=target AND (comedian_id IS NULL OR comedian_id=public_id) AND kind='comedian' AND identity_scope='entity';
   IF NOT FOUND THEN RAISE EXCEPTION 'Conflicting comedian identity %',public_id; END IF;
  END IF;
 ELSE
  SELECT id INTO target FROM curation_entities WHERE podcast_id=public_id;
  SELECT title INTO entity_label FROM podcasts WHERE id=public_id;
 END IF;
 IF entity_label IS NULL THEN RAISE EXCEPTION 'Missing legacy endpoint %:%',entity_kind,public_id; END IF;
 IF target IS NULL THEN
  target:='rollout:'||entity_kind||':'||public_id;
  INSERT INTO curation_entities(id,kind,label,comedian_id,podcast_id)
  VALUES(target,entity_kind,entity_label,CASE WHEN entity_kind='comedian' THEN public_id END,CASE WHEN entity_kind='podcast' THEN public_id END);
 END IF;
 RETURN target;
END $$;

-- Keep the old canonical path for negative-decision propagation before removing
-- unverified parent projections. A cycle is a hard failure, not guessed lineage.
CREATE TEMP TABLE rollout_roots ON COMMIT DROP AS
WITH RECURSIVE chain(original,id,path) AS (
 SELECT id,id,ARRAY[id] FROM comedians
 UNION ALL
 SELECT chain.original,c.parent_comedian_id,path||c.parent_comedian_id
 FROM chain JOIN comedians c ON c.id=chain.id
 WHERE c.parent_comedian_id IS NOT NULL AND NOT c.parent_comedian_id=ANY(path)
) SELECT chain.original,c.id AS root FROM chain JOIN comedians c ON c.id=chain.id WHERE c.parent_comedian_id IS NULL;
CREATE UNIQUE INDEX ON rollout_roots(original);
DO $$ BEGIN
 IF (SELECT count(*) FROM rollout_roots)<>(SELECT count(*) FROM comedians) THEN RAISE EXCEPTION 'Legacy parent cycle or missing endpoint requires reconciliation'; END IF;
END $$;

-- Already-active installations have already passed the graph preflights. Do not
-- reopen their reviewed edges or touch their source projections.
DO $$
DECLARE row record; edge text; s text; t text;
BEGIN
 IF to_regprocedure('curation_confirmed_parent(integer)') IS NOT NULL THEN RETURN; END IF;
 FOR row IN SELECT * FROM comedians WHERE parent_comedian_id IS NOT NULL ORDER BY id LOOP
  s:=pg_temp.stage_entity('comedian',row.id); t:=pg_temp.stage_entity('comedian',row.parent_comedian_id);
  INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind)
  VALUES(gen_random_uuid()::text,'alias_of',s,t,'comedian') ON CONFLICT(kind,source_id,target_id) DO NOTHING;
  SELECT id INTO edge FROM curation_relationships WHERE kind='alias_of' AND source_id=s AND target_id=t;
  INSERT INTO curation_observations(id,relationship_id,source,source_key,fingerprint,evidence,observed_at)
  VALUES(gen_random_uuid()::text,edge,'legacy-rollout:parent',row.id::text,md5(to_jsonb(row)::text),jsonb_build_object('legacyRow',to_jsonb(row),'disposition','pending_review','reason','Existing parent assignment is not approval evidence'),now()) ON CONFLICT DO NOTHING;
 END LOOP;
END $$;

-- Capture all source states, including negative decisions, before any status edit.
CREATE TEMP TABLE rollout_hosts ON COMMIT DROP AS
 SELECT 'comedian_podcasts'::text AS source_table,id::text AS source_id,comedian_id,podcast_id,association_type AS role,review_status AS state,to_jsonb(cp) AS evidence FROM comedian_podcasts cp WHERE association_type IN ('host','cohost') AND podcast_id IS NOT NULL
 UNION ALL
 SELECT 'podcast_candidate_reviews',id::text,comedian_id,podcast_id,association_type,candidate_status,to_jsonb(pc) FROM podcast_candidate_reviews pc WHERE association_type IN ('host','cohost') AND podcast_id IS NOT NULL;
DO $$
DECLARE row record; edge text; s text; t text; prior record; comic integer;
BEGIN
 IF to_regprocedure('curation_host_edge(integer,integer,text)') IS NOT NULL THEN RETURN; END IF;
 FOR row IN SELECT h.*,rr.root FROM rollout_hosts h JOIN rollout_roots rr ON rr.original=h.comedian_id ORDER BY h.source_table,h.source_id LOOP
  -- A rejection follows both the observed performer and their old canonical root.
  -- Removing an unverified alias must not allow that negative history to escape.
  FOR comic IN SELECT row.comedian_id UNION SELECT row.root WHERE row.state='rejected' LOOP
   s:=pg_temp.stage_entity('comedian',comic); t:=pg_temp.stage_entity('podcast',row.podcast_id);
   INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind)
   VALUES(gen_random_uuid()::text,row.role||'_of',s,t,'podcast') ON CONFLICT(kind,source_id,target_id) DO NOTHING;
   SELECT * INTO prior FROM curation_relationships WHERE kind=row.role||'_of' AND source_id=s AND target_id=t;
   edge:=prior.id;
   INSERT INTO curation_observations(id,relationship_id,source,source_key,fingerprint,evidence,observed_at)
   VALUES(gen_random_uuid()::text,edge,'legacy-rollout:'||row.source_table,row.source_id,md5(row.evidence::text),jsonb_build_object('legacyRow',row.evidence,'legacyCanonicalId',row.root,'observedComedianId',row.comedian_id),now()) ON CONFLICT DO NOTHING;
   IF row.state='rejected' AND prior.disposition IN ('proposed','confirmed') THEN
    INSERT INTO curation_decisions(id,relationship_id,version,action,before_state,after_state,actor,reason,evidence)
    VALUES(gen_random_uuid()::text,edge,prior.version+1,CASE WHEN prior.disposition='confirmed' THEN 'sever' ELSE 'reject' END,prior.disposition,CASE WHEN prior.disposition='confirmed' THEN 'severed' ELSE 'rejected' END,coalesce(nullif(row.evidence->>'reviewed_by',''),'legacy:unattributed'),'Preserved legacy host rejection during review cutover',jsonb_build_object('legacyRow',row.evidence,'sourceTable',row.source_table));
   END IF;
  END LOOP;
 END LOOP;
END $$;

DO $$ BEGIN
 IF to_regprocedure('curation_confirmed_parent(integer)') IS NULL THEN
  ALTER TABLE comedians DISABLE TRIGGER curation_comedian_write;
  UPDATE comedians c SET parent_comedian_id=NULL WHERE parent_comedian_id IS NOT NULL AND NOT EXISTS(
   SELECT 1 FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id
   WHERE r.kind='alias_of' AND r.disposition='confirmed' AND s.comedian_id=c.id AND t.comedian_id=c.parent_comedian_id);
  ALTER TABLE comedians ENABLE TRIGGER curation_comedian_write;
 END IF;
 IF to_regprocedure('curation_host_edge(integer,integer,text)') IS NULL THEN
  UPDATE comedian_podcasts cp SET review_status=CASE WHEN r.disposition IN ('rejected','severed') THEN 'rejected' ELSE 'pending' END
  FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id
  WHERE s.comedian_id=cp.comedian_id AND t.podcast_id=cp.podcast_id AND r.kind=cp.association_type||'_of' AND r.disposition<>'confirmed';
  UPDATE podcast_candidate_reviews pc SET candidate_status=CASE WHEN r.disposition IN ('rejected','severed') THEN 'rejected' ELSE 'pending' END
  FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id
  WHERE s.comedian_id=pc.comedian_id AND t.podcast_id=pc.podcast_id AND r.kind=pc.association_type||'_of' AND r.disposition<>'confirmed';
 END IF;
END $$;
UPDATE show_publication_revision SET revision=revision+1 WHERE id=1;
COMMIT;
