-- Run the read-only legacy decision preflight before deploy. Never infer approval
-- from discovery confidence or silently discard a legacy rejection.
CREATE FUNCTION curation_host_root(comic integer) RETURNS integer LANGUAGE sql STABLE AS $$
 WITH RECURSIVE chain(id,path) AS (
 SELECT comic,ARRAY[comic] UNION ALL
 SELECT c.parent_comedian_id,path||c.parent_comedian_id FROM chain JOIN comedians c ON c.id=chain.id
 WHERE c.parent_comedian_id IS NOT NULL AND NOT c.parent_comedian_id=ANY(path)
 ) SELECT c.id FROM chain JOIN comedians c ON c.id=chain.id WHERE c.parent_comedian_id IS NULL
$$;
DO $$ BEGIN
 IF EXISTS (
 SELECT 1 FROM (
 SELECT comedian_id,podcast_id,association_type,review_status state FROM comedian_podcasts
 UNION ALL SELECT comedian_id,podcast_id,association_type,candidate_status FROM podcast_candidate_reviews
 ) old WHERE old.association_type IN ('host','cohost') AND old.state IN ('accepted','rejected') AND NOT EXISTS (
 SELECT 1 FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id
 WHERE s.comedian_id=curation_host_root(old.comedian_id) AND t.podcast_id=old.podcast_id
 AND r.kind=old.association_type||'_of' AND ((old.state='accepted' AND r.disposition='confirmed') OR (old.state='rejected' AND r.disposition IN ('rejected','severed')))
 )) THEN RAISE EXCEPTION 'Reconcile legacy host decisions across sources before deploying host curation'; END IF;
END $$;
CREATE TABLE curation_host_bindings (
 comedian_id integer NOT NULL REFERENCES comedians(id) ON DELETE RESTRICT,
 podcast_id integer NOT NULL REFERENCES podcasts(id) ON DELETE RESTRICT,
 role text NOT NULL CHECK(role IN ('host','cohost')),
 relationship_id text NOT NULL REFERENCES curation_relationships(id) ON DELETE RESTRICT,
 PRIMARY KEY(comedian_id,podcast_id,role)
);
CREATE TABLE curation_host_reconciliations (
 id text PRIMARY KEY,
 comedian_id integer NOT NULL REFERENCES comedians(id) ON DELETE RESTRICT,
 podcast_id integer NOT NULL REFERENCES podcasts(id) ON DELETE RESTRICT,
 role text NOT NULL CHECK(role IN ('host','cohost')),
 old_relationship_id text NOT NULL REFERENCES curation_relationships(id) ON DELETE RESTRICT,
 new_relationship_id text NOT NULL REFERENCES curation_relationships(id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT now(),
 resolved_at timestamptz,actor text,reason text,reviewed_states jsonb,request_id text UNIQUE,preview_token text,
 CHECK((resolved_at IS NULL AND actor IS NULL AND reason IS NULL AND reviewed_states IS NULL AND request_id IS NULL AND preview_token IS NULL) OR
 (resolved_at IS NOT NULL AND length(btrim(actor))>0 AND length(btrim(reason))>0 AND jsonb_typeof(reviewed_states)='object' AND request_id IS NOT NULL AND preview_token IS NOT NULL))
);
CREATE UNIQUE INDEX curation_host_open_reconciliation ON curation_host_reconciliations(comedian_id,podcast_id,role,old_relationship_id,new_relationship_id) WHERE resolved_at IS NULL;
CREATE TRIGGER curation_host_reconciliation_retained BEFORE DELETE ON curation_host_reconciliations FOR EACH ROW EXECUTE FUNCTION curation_immutable_record();
CREATE FUNCTION curation_host_edge(comic integer,podcast integer,role text) RETURNS text LANGUAGE sql STABLE AS $$
 SELECT r.id FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id
 WHERE r.kind=role||'_of' AND s.comedian_id=curation_host_root(comic) AND t.podcast_id=podcast
$$;
CREATE FUNCTION curation_observe_host(comic integer,podcast integer,role text,source text,source_key text,evidence jsonb) RETURNS text LANGUAGE plpgsql AS $$
DECLARE canonical integer; s text; t text; edge text; previous text;
BEGIN
 PERFORM curation_lock_intake();
 IF role NOT IN ('host','cohost') OR jsonb_typeof(evidence) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'Invalid host role/evidence' USING ERRCODE='23514'; END IF;
 canonical:=curation_host_root(comic);
 IF canonical IS NULL THEN RAISE EXCEPTION 'Unresolved comedian identity' USING ERRCODE='23514'; END IF;
 s:=curation_parent_entity(canonical);
 SELECT id INTO t FROM curation_entities WHERE podcast_id=podcast;
 IF t IS NULL THEN RAISE EXCEPTION 'Podcast identity must be staged first' USING ERRCODE='23514'; END IF;
 INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind)
 VALUES(gen_random_uuid()::text,role||'_of',s,t,'podcast') ON CONFLICT(kind,source_id,target_id) DO NOTHING;
 edge:=curation_host_edge(comic,podcast,role);
 SELECT relationship_id INTO previous FROM curation_host_bindings WHERE comedian_id=comic AND podcast_id=podcast AND curation_host_bindings.role=curation_observe_host.role;
 IF previous IS NOT NULL AND previous<>edge THEN
 INSERT INTO curation_host_reconciliations(id,comedian_id,podcast_id,role,old_relationship_id,new_relationship_id)
 VALUES(gen_random_uuid()::text,comic,podcast,role,previous,edge) ON CONFLICT DO NOTHING;
 END IF;
 INSERT INTO curation_host_bindings VALUES(comic,podcast,role,edge)
 ON CONFLICT ON CONSTRAINT curation_host_bindings_pkey DO UPDATE SET relationship_id=EXCLUDED.relationship_id;
 INSERT INTO curation_observations(id,relationship_id,source,source_key,fingerprint,evidence,observed_at)
 VALUES(gen_random_uuid()::text,edge,source,source_key,md5(evidence::text||comic),evidence||jsonb_build_object('requestedComedianId',comic,'canonicalComedianId',canonical),now()) ON CONFLICT DO NOTHING;
 RETURN edge;
END $$;
CREATE FUNCTION curation_host_allowed(edge text) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(SELECT 1 FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id JOIN comedians c ON c.id=s.comedian_id
 WHERE r.id=edge AND r.kind IN ('host_of','cohost_of') AND r.disposition='confirmed' AND s.disposition='approved'
 AND c.visible AND c.identity_validated_at IS NOT NULL AND c.parent_comedian_id IS NULL
 AND NOT EXISTS(SELECT 1 FROM comedian_deny_list d WHERE curation_exact_name(d.name)=curation_exact_name(c.name))
 AND EXISTS(SELECT 1 FROM curation_comedian_policy(c.uuid,c.name,c.id) policy WHERE policy.disposition='approved') AND curation_podcast_allowed(t.podcast_id)
 AND NOT EXISTS(SELECT 1 FROM curation_host_reconciliations h WHERE h.resolved_at IS NULL AND (h.old_relationship_id=edge OR h.new_relationship_id=edge)))
$$;
CREATE FUNCTION curation_validate_host(edge text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id JOIN comedians c ON c.id=s.comedian_id
 WHERE r.id=edge AND r.kind IN ('host_of','cohost_of') AND s.disposition='approved' AND c.visible AND c.identity_validated_at IS NOT NULL AND c.parent_comedian_id IS NULL
 AND NOT EXISTS(SELECT 1 FROM comedian_deny_list d WHERE curation_exact_name(d.name)=curation_exact_name(c.name)) AND EXISTS(SELECT 1 FROM curation_comedian_policy(c.uuid,c.name,c.id) policy WHERE policy.disposition='approved') AND curation_podcast_allowed(t.podcast_id)) THEN
 RAISE EXCEPTION 'Host confirmation requires independently approved eligible endpoints' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM curation_host_reconciliations WHERE resolved_at IS NULL AND (old_relationship_id=edge OR new_relationship_id=edge)) THEN
 RAISE EXCEPTION 'Review canonical identity reconciliation and conflicting host decisions first' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM curation_observations WHERE relationship_id=edge) THEN RAISE EXCEPTION 'Host evidence is required' USING ERRCODE='23514'; END IF;
END $$;
CREATE FUNCTION curation_host_write() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE edge text; state text; role text; payload jsonb; latest record;
BEGIN
 role:=NEW.association_type;
 IF TG_OP='UPDATE' AND (NEW.comedian_id,NEW.podcast_id,NEW.association_type,NEW.source) IS DISTINCT FROM (OLD.comedian_id,OLD.podcast_id,OLD.association_type,OLD.source) THEN
  IF OLD.association_type IN ('host','cohost') AND OLD.podcast_id IS NOT NULL THEN RAISE EXCEPTION 'Host endpoints/source are immutable; propose the new pair separately' USING ERRCODE='23514'; END IF; END IF;
 IF role NOT IN ('host','cohost') OR role IS NULL THEN RETURN NEW; END IF;
 IF NEW.podcast_id IS NULL THEN
  INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at)
  VALUES(gen_random_uuid()::text,curation_parent_entity(curation_host_root(NEW.comedian_id)),NEW.source,TG_TABLE_NAME||':'||NEW.id,md5(to_jsonb(NEW)::text),to_jsonb(NEW),now()) ON CONFLICT DO NOTHING;
  IF TG_TABLE_NAME='podcast_candidate_reviews' THEN NEW.candidate_status:='pending'; END IF;
  RETURN NEW;
 END IF;
 payload:=to_jsonb(NEW);
 -- Projection updates do not create synthetic source observations or relink
 -- provenance. All top-level discovery writes are retained before policy coercion.
 IF pg_trigger_depth()<=1 THEN
  edge:=curation_observe_host(NEW.comedian_id,NEW.podcast_id,role,NEW.source,TG_TABLE_NAME||':'||NEW.id,payload);
 ELSE edge:=curation_host_edge(NEW.comedian_id,NEW.podcast_id,role); END IF;
 SELECT disposition INTO state FROM curation_relationships WHERE id=edge;
 SELECT actor,created_at INTO latest FROM curation_decisions WHERE relationship_id=edge ORDER BY version DESC LIMIT 1;
 NEW.reviewed_by:=latest.actor; NEW.reviewed_at:=latest.created_at;
 IF TG_TABLE_NAME='podcast_candidate_reviews' THEN
  NEW.candidate_status:=CASE WHEN state IN ('rejected','severed') THEN 'rejected' WHEN curation_host_allowed(edge) THEN 'accepted' ELSE 'pending' END;
 ELSE
  NEW.review_status:=CASE WHEN state IN ('rejected','severed') THEN 'rejected'
   WHEN curation_host_allowed(edge) AND NEW.comedian_id=curation_host_root(NEW.comedian_id) AND NEW.source='curation' THEN 'accepted'
   WHEN curation_host_allowed(edge) THEN 'superseded' ELSE 'pending' END;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION curation_project_host(edge text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE e record; latest record; role text;
BEGIN
 SELECT r.*,s.comedian_id,t.podcast_id INTO e FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE r.id=edge AND r.kind IN ('host_of','cohost_of');
 IF NOT FOUND OR e.comedian_id IS NULL OR e.podcast_id IS NULL THEN RETURN; END IF;
 role:=replace(e.kind,'_of','');
 SELECT actor,created_at INTO latest FROM curation_decisions WHERE relationship_id=edge ORDER BY version DESC LIMIT 1;
 UPDATE podcast_candidate_reviews SET candidate_status=CASE WHEN e.disposition IN ('rejected','severed') THEN 'rejected' WHEN curation_host_allowed(edge) THEN 'accepted' ELSE 'pending' END,reviewed_by=latest.actor,reviewed_at=latest.created_at,updated_at=now()
 WHERE podcast_id=e.podcast_id AND association_type=role AND curation_host_root(comedian_id)=e.comedian_id;
 UPDATE comedian_podcasts SET review_status='pending',updated_at=now()
 WHERE podcast_id=e.podcast_id AND association_type=role AND (comedian_id=e.comedian_id OR curation_host_root(comedian_id)=e.comedian_id);
 IF curation_host_allowed(edge) THEN
 INSERT INTO comedian_podcasts(comedian_id,podcast_id,association_type,source,review_status,confidence,evidence,reviewed_at,reviewed_by,updated_at)
 VALUES(e.comedian_id,e.podcast_id,role,'curation','accepted',1,jsonb_build_object('relationshipId',edge),latest.created_at,latest.actor,now())
 ON CONFLICT(comedian_id,podcast_id,association_type,source) DO UPDATE SET review_status='accepted',reviewed_at=EXCLUDED.reviewed_at,reviewed_by=EXCLUDED.reviewed_by,updated_at=now();
 END IF;
 UPDATE show_publication_revision SET revision=revision+1 WHERE id=1;
END $$;
CREATE FUNCTION curation_host_decision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.action='confirm' AND EXISTS(SELECT 1 FROM curation_relationships WHERE id=NEW.relationship_id AND kind IN ('host_of','cohost_of')) THEN PERFORM curation_validate_host(NEW.relationship_id); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_host_decision_guard BEFORE INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_host_decision_guard();
CREATE FUNCTION curation_host_decision_projection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b record; edge record; new_edge text; affected text[]:=ARRAY[]::text[];
BEGIN
 IF NEW.relationship_id IS NOT NULL THEN
  PERFORM curation_project_host(NEW.relationship_id);
  IF EXISTS(SELECT 1 FROM curation_relationships WHERE id=NEW.relationship_id AND kind='alias_of') THEN
   FOR b IN SELECT * FROM curation_host_bindings binding WHERE binding.relationship_id IS DISTINCT FROM curation_host_edge(binding.comedian_id,binding.podcast_id,binding.role) LOOP
    IF b.relationship_id IS DISTINCT FROM curation_host_edge(b.comedian_id,b.podcast_id,b.role) THEN
     new_edge:=curation_observe_host(b.comedian_id,b.podcast_id,b.role,'canonical-reconciliation',NEW.id,jsonb_build_object('parentDecisionId',NEW.id,'previousRelationshipId',b.relationship_id));
     affected:=affected||ARRAY[b.relationship_id,new_edge];
    END IF;
   END LOOP;
   FOR edge IN SELECT DISTINCT unnest(affected) id LOOP PERFORM curation_project_host(edge.id); END LOOP;
  END IF;
 ELSE
  FOR edge IN SELECT id FROM curation_relationships WHERE kind IN ('host_of','cohost_of') AND (source_id=NEW.entity_id OR target_id=NEW.entity_id OR source_id IN (
 SELECT canonical.id FROM curation_entities changed JOIN curation_entities canonical ON canonical.comedian_id=curation_host_root(changed.comedian_id) WHERE changed.id=NEW.entity_id)) LOOP PERFORM curation_project_host(edge.id); END LOOP;
 END IF;
 RETURN NEW;
END $$;
-- Runs after the parent FK projection so canonical rekeys see the committed shape.
CREATE TRIGGER zzz_curation_host_projection AFTER INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_host_decision_projection();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON comedian_podcasts FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON podcast_candidate_reviews FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER curation_host_write BEFORE INSERT OR UPDATE ON comedian_podcasts FOR EACH ROW EXECUTE FUNCTION curation_host_write();
CREATE TRIGGER curation_host_write BEFORE INSERT OR UPDATE ON podcast_candidate_reviews FOR EACH ROW EXECUTE FUNCTION curation_host_write();
-- Legacy source rows and their evidence are retained; confirmed attribution has
-- exactly one curation projection. Deployment preflight prevents unreviewed drift.
CREATE TEMP TABLE curation_host_backfill ON COMMIT DROP AS
 SELECT source_table,payload,(payload->>'comedian_id')::integer comedian_id,
 curation_host_root((payload->>'comedian_id')::integer) canonical_id,
 (payload->>'podcast_id')::integer podcast_id,payload->>'association_type' role
 FROM (
 SELECT 'comedian_podcasts' source_table,to_jsonb(cp) payload FROM comedian_podcasts cp WHERE association_type IN ('host','cohost')
 UNION ALL SELECT 'podcast_candidate_reviews',to_jsonb(cr) FROM podcast_candidate_reviews cr WHERE association_type IN ('host','cohost') AND podcast_id IS NOT NULL
 ) source_rows;
ANALYZE curation_host_backfill;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM curation_host_backfill b LEFT JOIN curation_entities p ON p.podcast_id=b.podcast_id WHERE b.canonical_id IS NULL OR p.id IS NULL) THEN
 RAISE EXCEPTION 'Reconcile unresolved host endpoints before backfill'; END IF;
 IF EXISTS(SELECT 1 FROM curation_host_backfill b JOIN comedians c ON c.id=b.canonical_id JOIN curation_identity_keys k ON k.namespace='comedian-uuid:v1' AND k.scope='global' AND k.value=c.uuid
 WHERE NOT EXISTS(SELECT 1 FROM curation_entities e WHERE e.comedian_id=b.canonical_id)) THEN
 RAISE EXCEPTION 'Reconcile unbound comedian identity keys before host backfill'; END IF;
END $$;
INSERT INTO curation_entities(id,kind,label,comedian_id)
 SELECT DISTINCT 'comedian-parent:'||c.id,'comedian',c.name,c.id FROM curation_host_backfill b JOIN comedians c ON c.id=b.canonical_id
 WHERE NOT EXISTS(SELECT 1 FROM curation_entities e WHERE e.comedian_id=c.id);
INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
 SELECT gen_random_uuid()::text,e.id,'comedian','entity','external_id','comedian-uuid:v1','global',c.uuid
 FROM comedians c JOIN curation_entities e ON e.comedian_id=c.id
 WHERE EXISTS(SELECT 1 FROM curation_host_backfill b WHERE b.canonical_id=c.id) ON CONFLICT DO NOTHING;
INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind)
 SELECT gen_random_uuid()::text,pair.role||'_of',pair.source_id,pair.target_id,'podcast' FROM (
 SELECT DISTINCT b.role,s.id source_id,t.id target_id FROM curation_host_backfill b
 JOIN curation_entities s ON s.comedian_id=b.canonical_id JOIN curation_entities t ON t.podcast_id=b.podcast_id
 ) pair ON CONFLICT(kind,source_id,target_id) DO NOTHING;
INSERT INTO curation_host_bindings(comedian_id,podcast_id,role,relationship_id)
 SELECT DISTINCT b.comedian_id,b.podcast_id,b.role,r.id FROM curation_host_backfill b
 JOIN curation_entities s ON s.comedian_id=b.canonical_id JOIN curation_entities t ON t.podcast_id=b.podcast_id
 JOIN curation_relationships r ON r.source_id=s.id AND r.target_id=t.id AND r.kind=b.role||'_of';
INSERT INTO curation_observations(id,relationship_id,source,source_key,fingerprint,evidence,observed_at)
 SELECT gen_random_uuid()::text,r.relationship_id,b.payload->>'source',b.source_table||':'||(b.payload->>'id'),md5(b.payload::text||b.comedian_id),b.payload||jsonb_build_object('requestedComedianId',b.comedian_id,'canonicalComedianId',b.canonical_id),now()
 FROM curation_host_backfill b JOIN curation_host_bindings r ON r.comedian_id=b.comedian_id AND r.podcast_id=b.podcast_id AND r.role=b.role
 ON CONFLICT DO NOTHING;
DO $$ DECLARE edge record; BEGIN
 -- Pending proposals need no publication update; project only reviewed pairs.
 FOR edge IN SELECT id FROM curation_relationships WHERE kind IN ('host_of','cohost_of') AND disposition<>'proposed' LOOP PERFORM curation_project_host(edge.id); END LOOP;
END $$;

CREATE FUNCTION curation_guard_host_projection_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.source='curation' AND OLD.association_type IN ('host','cohost') THEN RAISE EXCEPTION 'Sever the host relationship instead of deleting its projection' USING ERRCODE='23514'; END IF;
 RETURN OLD;
END $$;
CREATE TRIGGER curation_host_projection_delete BEFORE DELETE ON comedian_podcasts FOR EACH ROW EXECUTE FUNCTION curation_guard_host_projection_delete();
CREATE FUNCTION curation_guard_host_reconciliation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM curation_lock_intake();
 IF OLD.resolved_at IS NOT NULL OR (to_jsonb(NEW)-ARRAY['resolved_at','actor','reason','reviewed_states','request_id','preview_token']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['resolved_at','actor','reason','reviewed_states','request_id','preview_token']) OR NEW.resolved_at IS NULL THEN RAISE EXCEPTION 'Host identity reconciliation is immutable after review' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_host_reconciliation_update BEFORE UPDATE ON curation_host_reconciliations FOR EACH ROW EXECUTE FUNCTION curation_guard_host_reconciliation();
CREATE FUNCTION curation_refresh_host_visibility() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE edge record;
BEGIN
 IF NEW.visible IS DISTINCT FROM OLD.visible OR NEW.identity_validated_at IS DISTINCT FROM OLD.identity_validated_at THEN
 FOR edge IN SELECT r.id FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id WHERE r.kind IN ('host_of','cohost_of') AND s.comedian_id=curation_host_root(NEW.id) LOOP PERFORM curation_project_host(edge.id); END LOOP;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER zz_curation_host_visibility AFTER UPDATE ON comedians FOR EACH ROW EXECUTE FUNCTION curation_refresh_host_visibility();

CREATE FUNCTION curation_preview_host_rekey(child integer,parent integer) RETURNS jsonb LANGUAGE sql STABLE AS $$
 WITH RECURSIVE members(id) AS (SELECT child UNION SELECT c.id FROM comedians c JOIN members m ON c.parent_comedian_id=m.id),
 destination AS (SELECT coalesce(curation_host_root(parent),child) id)
 SELECT coalesce(jsonb_agg(to_jsonb(impact) ORDER BY impact.old_relationship_id,impact.comedian_id),'[]'::jsonb) FROM (
 SELECT b.comedian_id,b.podcast_id,b.role,b.relationship_id old_relationship_id,r.disposition old_state,r.version old_version,
 n.id new_relationship_id,coalesce(n.disposition,'proposed') new_state,n.version new_version,d.id new_comedian_id
 FROM curation_host_bindings b JOIN members m ON m.id=b.comedian_id JOIN curation_relationships r ON r.id=b.relationship_id
 JOIN curation_entities old ON old.id=r.source_id CROSS JOIN destination d
 LEFT JOIN curation_entities target ON target.comedian_id=d.id
 LEFT JOIN curation_relationships n ON n.source_id=target.id AND n.target_id=r.target_id AND n.kind=r.kind
 WHERE old.comedian_id<>d.id
 ) impact
$$;
