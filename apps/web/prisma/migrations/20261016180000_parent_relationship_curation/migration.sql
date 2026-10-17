-- Deployment preflight: reconcile legacy parent edits explicitly before applying
-- this boundary. Never silently bless inferred aliases or discard their lineage.
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM comedians c WHERE c.parent_comedian_id IS NOT NULL AND NOT EXISTS(
 SELECT 1 FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id
 WHERE r.kind='alias_of' AND r.disposition='confirmed' AND s.comedian_id=c.id AND t.comedian_id=c.parent_comedian_id)) THEN
 RAISE EXCEPTION 'Unreviewed legacy parent links: reconcile and preview existing parent assignments before deploying parent curation'; END IF;
 IF EXISTS(SELECT 1 FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id LEFT JOIN comedians c ON c.id=s.comedian_id
 WHERE r.kind='alias_of' AND r.disposition='confirmed' AND (s.comedian_id IS NULL OR t.comedian_id IS NULL OR c.parent_comedian_id IS DISTINCT FROM t.comedian_id)) THEN
 RAISE EXCEPTION 'Confirmed parent ledger differs from public lineage: reconcile before deploying parent curation'; END IF;
END $$;
CREATE FUNCTION curation_parent_entity(public_id integer) RETURNS text LANGUAGE plpgsql AS $$
DECLARE target text; comic record;
BEGIN
 PERFORM curation_lock_intake();
 SELECT * INTO comic FROM comedians WHERE id=public_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Comedian endpoint not found' USING ERRCODE='23503'; END IF;
 SELECT id INTO target FROM curation_entities WHERE comedian_id=public_id;
 IF target IS NULL THEN
  SELECT e.id INTO target FROM curation_identity_keys k JOIN curation_entities e ON e.id=k.entity_id
  WHERE k.namespace='comedian-uuid:v1' AND k.scope='global' AND k.value=comic.uuid;
  IF target IS NOT NULL THEN
   RAISE EXCEPTION 'Comedian identity binding requires reconciliation before proposing a parent' USING ERRCODE='23514';
  END IF;
  target:='comedian-parent:'||public_id;
  INSERT INTO curation_entities(id,kind,label,comedian_id) VALUES(target,'comedian',comic.name,public_id);
  INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
  VALUES(gen_random_uuid()::text,target,'comedian','entity','external_id','comedian-uuid:v1','global',comic.uuid) ON CONFLICT DO NOTHING;
 END IF;
 RETURN target;
END $$;
CREATE FUNCTION curation_propose_parent(child integer,parent integer,evidence jsonb,actor text,reason text,source text DEFAULT 'admin-parent-review') RETURNS text LANGUAGE plpgsql AS $$
DECLARE child_entity text; parent_entity text; relationship text;
BEGIN
 PERFORM curation_lock_intake();
 IF child=parent THEN RAISE EXCEPTION 'A comedian cannot be their own parent' USING ERRCODE='23514'; END IF;
 IF jsonb_typeof(evidence)<>'object' OR nullif(btrim(actor),'') IS NULL OR nullif(btrim(reason),'') IS NULL THEN RAISE EXCEPTION 'Proposal requires evidence, actor and reason' USING ERRCODE='23514'; END IF;
 child_entity:=curation_parent_entity(child); parent_entity:=curation_parent_entity(parent);
 INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind)
 VALUES(gen_random_uuid()::text,'alias_of',child_entity,parent_entity,'comedian') ON CONFLICT(kind,source_id,target_id) DO NOTHING;
 SELECT id INTO relationship FROM curation_relationships WHERE kind='alias_of' AND source_id=child_entity AND target_id=parent_entity;
 INSERT INTO curation_observations(id,relationship_id,source,source_key,fingerprint,evidence,observed_at)
 VALUES(gen_random_uuid()::text,relationship,source,child||':'||parent,md5(evidence::text||actor||reason),evidence||jsonb_build_object('actor',actor,'reason',reason),now()) ON CONFLICT DO NOTHING;
 RETURN relationship;
END $$;
CREATE FUNCTION curation_confirmed_parent(child integer) RETURNS integer LANGUAGE sql STABLE AS $$
 SELECT t.comedian_id FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id
 WHERE r.kind='alias_of' AND r.disposition='confirmed' AND s.comedian_id=child
$$;
CREATE FUNCTION curation_validate_parent(relationship text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE edge record;
BEGIN
 SELECT r.*,s.comedian_id AS child,t.comedian_id AS parent,s.disposition AS child_state,t.disposition AS parent_state INTO edge FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE r.id=relationship AND r.kind='alias_of';
 IF NOT FOUND THEN RAISE EXCEPTION 'Parent relationship not found' USING ERRCODE='23503'; END IF;
 IF edge.child IS NULL OR edge.parent IS NULL OR edge.child_state<>'approved' OR edge.parent_state<>'approved'
 OR NOT EXISTS(SELECT 1 FROM comedians WHERE id=edge.child AND visible AND identity_validated_at IS NOT NULL)
 OR NOT EXISTS(SELECT 1 FROM comedians WHERE id=edge.parent AND visible AND identity_validated_at IS NOT NULL AND parent_comedian_id IS NULL)
 OR EXISTS(SELECT 1 FROM comedians c JOIN comedian_deny_list d ON curation_exact_name(d.name)=curation_exact_name(c.name) WHERE c.id IN(edge.child,edge.parent)) THEN
 RAISE EXCEPTION 'Both performers require independent identity approval; choose an eligible canonical parent' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM curation_observations WHERE relationship_id=relationship AND source='admin-parent-review' AND evidence->>'samePerformer'='true' AND evidence->>'sourceUrl' ~ '^https?://' AND length(btrim(evidence->>'explanation'))>=20) THEN
 RAISE EXCEPTION 'Independent same-performer evidence is required; embedded names and event titles are not alias evidence' USING ERRCODE='23514'; END IF;
END $$;
CREATE FUNCTION curation_guard_parent_decision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.action='confirm' AND EXISTS(SELECT 1 FROM curation_relationships WHERE id=NEW.relationship_id AND kind='alias_of') THEN PERFORM curation_validate_parent(NEW.relationship_id); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_parent_decision_guard BEFORE INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_guard_parent_decision();
CREATE FUNCTION curation_guard_parent_projection() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (TG_OP='INSERT' AND NEW.parent_comedian_id IS NOT NULL) OR (TG_OP='UPDATE' AND NEW.parent_comedian_id IS DISTINCT FROM OLD.parent_comedian_id) THEN
  IF NEW.parent_comedian_id IS DISTINCT FROM curation_confirmed_parent(NEW.id) THEN
   RAISE EXCEPTION 'Parent edits require a reviewed curation decision' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER ab_parent_projection BEFORE INSERT OR UPDATE ON comedians FOR EACH ROW EXECUTE FUNCTION curation_guard_parent_projection();
CREATE FUNCTION curation_project_parent_decision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE child integer;
BEGIN
 SELECT e.comedian_id INTO child FROM curation_relationships r JOIN curation_entities e ON e.id=r.source_id WHERE r.id=NEW.relationship_id AND r.kind='alias_of';
 IF child IS NOT NULL THEN
  UPDATE comedians SET parent_comedian_id=curation_confirmed_parent(child) WHERE id=child;
  IF EXISTS(SELECT 1 FROM comedians WHERE id=child AND parent_comedian_id IS DISTINCT FROM curation_confirmed_parent(child)) THEN RAISE EXCEPTION 'Parent projection did not apply'; END IF;
  UPDATE show_publication_revision SET revision=revision+1 WHERE id=1;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER zz_curation_parent_projection AFTER INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_project_parent_decision();

CREATE OR REPLACE FUNCTION curation_guard_comedian_write() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE result record;
BEGIN
 IF TG_OP='UPDATE' AND (to_jsonb(NEW)-'parent_comedian_id') IS NOT DISTINCT FROM (to_jsonb(OLD)-'parent_comedian_id') AND NEW.parent_comedian_id IS NOT DISTINCT FROM curation_confirmed_parent(NEW.id) THEN RETURN NEW; END IF;
 IF TG_OP='UPDATE' AND NEW.identity_validated_at IS NULL AND NEW.identity_validated_by IS NULL AND
 (to_jsonb(NEW)-ARRAY['identity_validated_at','identity_validated_by']) IS NOT DISTINCT FROM
 (to_jsonb(OLD)-ARRAY['identity_validated_at','identity_validated_by']) THEN RETURN NEW; END IF;
 -- Visibility is presentation only. Even showing a blocked profile leaves policy intact.
 IF TG_OP='UPDATE' AND (to_jsonb(NEW)-ARRAY['visible','block_reason','block_added_by','block_added_at']) IS NOT DISTINCT FROM
 (to_jsonb(OLD)-ARRAY['visible','block_reason','block_added_by','block_added_at']) THEN RETURN NEW; END IF;
 SELECT * INTO result FROM curation_comedian_policy(NEW.uuid,NEW.name,CASE WHEN TG_OP='UPDATE' THEN OLD.id ELSE NULL END,curation_comedian_row_keys(to_jsonb(NEW)));
 IF result.disposition<>'approved' OR result.entity_id IS NULL THEN
   PERFORM curation_observe_comedian(NEW.uuid,NEW.name,jsonb_build_object('operation',TG_OP,'writer','comedians','row',to_jsonb(NEW)),curation_comedian_row_keys(to_jsonb(NEW)));
   IF TG_OP='UPDATE' THEN RETURN OLD; ELSE
     IF result.disposition='pending' THEN INSERT INTO comedian_identity_candidates(uuid,name) VALUES(NEW.uuid,NEW.name) ON CONFLICT DO NOTHING; END IF;
     RETURN NULL; END IF;
 END IF;
 IF TG_OP='INSERT' AND result.comedian_id IS NOT NULL THEN RETURN NULL; END IF;
 PERFORM curation_observe_comedian(NEW.uuid,NEW.name,jsonb_build_object('writer','approved-write'),curation_comedian_row_keys(to_jsonb(NEW)));
 RETURN NEW;
END $$;
