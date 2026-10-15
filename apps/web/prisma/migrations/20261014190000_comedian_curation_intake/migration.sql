-- Durable admission boundary shared by Prisma, scraper SQL and maintenance imports.
-- No legacy identities are implicitly approved. Reconcile/backfill before deployment.
CREATE TABLE curation_intake_lock(id integer PRIMARY KEY CHECK(id=1), version bigint NOT NULL DEFAULT 0);
INSERT INTO curation_intake_lock(id) VALUES(1);
CREATE FUNCTION curation_lock_intake() RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 UPDATE curation_intake_lock SET version=version+1 WHERE id=1;
 IF NOT FOUND THEN RAISE EXCEPTION 'Curation policy unavailable'; END IF;
END $$;
CREATE FUNCTION curation_serialize_intake() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN PERFORM curation_lock_intake(); RETURN NULL; END $$;
-- Statement locks precede row locks; a real write also rejects stale RR snapshots.
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON curation_entities FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON curation_identity_keys FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON curation_relationships FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT ON curation_decisions FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON comedian_deny_list FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON comedians FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE ON lineup_items FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE ON comedian_identity_candidates FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();

CREATE FUNCTION curation_exact_name(value text) RETURNS text LANGUAGE sql IMMUTABLE STRICT AS $$
 SELECT normalize(lower(btrim(regexp_replace(normalize(value,NFC),
 U&'[\0009-\000D\0020\0085\00A0\1680\2000-\200A\2028\2029\202F\205F\3000]+',' ','g'))),NFC)
$$;
CREATE INDEX curation_comedian_label ON curation_entities(curation_exact_name(label)) WHERE kind='comedian';
CREATE INDEX curation_comedian_name ON comedians(curation_exact_name(name));
CREATE INDEX curation_denied_comedian_name ON comedian_deny_list(curation_exact_name(name));

-- Keys are exact and namespace-scoped. Names never use substring matching.
-- Names can hold an ambiguous identity, but never merge two identities.
CREATE FUNCTION curation_comedian_matches(input_uuid text, input_name text, input_id integer DEFAULT NULL, input_keys jsonb DEFAULT '[]')
RETURNS TABLE(id text) LANGUAGE sql STABLE AS $$
 WITH RECURSIVE matched(id) AS (
 SELECT e.id FROM curation_entities e WHERE e.kind='comedian' AND (
   e.comedian_id=input_id OR curation_exact_name(e.label)=curation_exact_name(input_name)
   OR EXISTS(SELECT 1 FROM curation_identity_keys k WHERE k.entity_id=e.id AND (
    (k.namespace='comedian-uuid:v1' AND k.scope='global' AND k.value=input_uuid)
    OR (k.namespace LIKE 'legacy:%:comedian_uuid:v1' AND k.value=input_uuid)
    OR (k.namespace LIKE 'legacy:%:comedian_identity_candidates:v1' AND k.value=input_uuid)
    OR (k.namespace='exact-name:v1' AND k.scope='global' AND k.value=curation_exact_name(input_name))
    OR EXISTS(SELECT 1 FROM jsonb_array_elements(input_keys) j WHERE k.namespace=j->>'namespace' AND k.scope=j->>'scope' AND k.value=j->>'value')
   )))
 UNION
 SELECT CASE WHEN r.source_id=m.id THEN r.target_id ELSE r.source_id END
 FROM matched m JOIN curation_relationships r ON (r.source_id=m.id OR r.target_id=m.id)
 WHERE r.kind='alias_of' AND r.disposition='confirmed'
 ) SELECT id FROM matched
$$;
CREATE FUNCTION curation_comedian_policy(input_uuid text, input_name text, input_id integer DEFAULT NULL, input_keys jsonb DEFAULT '[]')
RETURNS TABLE(disposition text, entity_id text, comedian_id integer) LANGUAGE plpgsql STABLE AS $$
DECLARE ids text[]; roots text[]; selected_id text;
BEGIN
 SELECT array_agg(m.id) INTO ids FROM curation_comedian_matches(input_uuid,input_name,input_id,input_keys) m;
 IF EXISTS(SELECT 1 FROM curation_entities e WHERE e.id=ANY(ids) AND e.disposition='blocked')
 OR EXISTS(SELECT 1 FROM comedian_deny_list d WHERE curation_exact_name(d.name)=curation_exact_name(input_name)
    OR EXISTS(SELECT 1 FROM curation_entities e WHERE e.id=ANY(ids) AND curation_exact_name(e.label)=curation_exact_name(d.name)))
 OR EXISTS(SELECT 1 FROM comedians c WHERE NOT c.visible AND (c.id=input_id OR c.uuid=input_uuid OR curation_exact_name(c.name)=curation_exact_name(input_name)
    OR EXISTS(SELECT 1 FROM curation_entities e WHERE e.id=ANY(ids) AND (e.comedian_id=c.id OR curation_exact_name(e.label)=curation_exact_name(c.name)))))
 OR EXISTS(SELECT 1 FROM comedian_identity_candidates c WHERE c.status='rejected' AND (c.uuid=input_uuid OR curation_exact_name(c.name)=curation_exact_name(input_name))) THEN
   RETURN QUERY SELECT 'blocked'::text, (SELECT e.id FROM curation_entities e WHERE e.id=ANY(ids) AND e.disposition='blocked' ORDER BY e.id LIMIT 1), NULL::integer; RETURN;
 END IF;
 SELECT array_agg(e.id) INTO roots FROM curation_entities e WHERE e.id=ANY(ids) AND e.identity_scope='entity'
 AND NOT EXISTS(SELECT 1 FROM curation_relationships r WHERE r.source_id=e.id AND r.kind='alias_of' AND r.disposition='confirmed');
 IF cardinality(roots)=1 THEN selected_id:=roots[1]; END IF;
 RETURN QUERY SELECT CASE WHEN selected_id IS NOT NULL
   AND NOT EXISTS(SELECT 1 FROM curation_entities e WHERE e.id=ANY(ids) AND e.identity_scope='entity' AND e.disposition<>'approved')
   AND NOT EXISTS(SELECT 1 FROM comedians c WHERE (c.uuid=input_uuid OR c.id=input_id) AND c.parent_comedian_id IS NOT NULL
     AND NOT EXISTS(SELECT 1 FROM curation_entities e JOIN curation_relationships r ON r.source_id=e.id
       JOIN curation_entities p ON p.id=r.target_id WHERE e.comedian_id=c.id AND p.comedian_id=c.parent_comedian_id AND r.kind='alias_of' AND r.disposition='confirmed'))
 THEN 'approved' ELSE 'pending' END,
 selected_id, (SELECT e.comedian_id FROM curation_entities e WHERE e.id=selected_id);
END $$;

CREATE FUNCTION curation_observe_comedian(input_uuid text,input_name text,evidence jsonb DEFAULT '{}',input_keys jsonb DEFAULT '[]')
RETURNS text LANGUAGE plpgsql AS $$
DECLARE result record; target text; matched text[]; k jsonb;
BEGIN
 PERFORM curation_lock_intake();
 SELECT * INTO result FROM curation_comedian_policy(input_uuid,input_name,(SELECT id FROM comedians WHERE uuid=input_uuid),input_keys);
 target:=result.entity_id;
 SELECT array_agg(m.id) INTO matched FROM curation_comedian_matches(input_uuid,input_name,(SELECT id FROM comedians WHERE uuid=input_uuid),input_keys) m;
 IF target IS NULL AND cardinality(matched)=1 THEN target:=matched[1]; END IF;
 IF target IS NULL OR EXISTS(SELECT 1 FROM curation_entities WHERE id=target AND identity_scope<>'entity') THEN
   -- A stable candidate identity holds ambiguity; do not attach ambiguous provider keys.
   target:='comedian-intake:'||md5(input_uuid);
   INSERT INTO curation_entities(id,kind,label) VALUES(target,'comedian',input_name) ON CONFLICT(id) DO NOTHING;
 END IF;
 IF result.disposition='blocked' AND NOT EXISTS(SELECT 1 FROM curation_entities WHERE id=target AND disposition='blocked') THEN
   INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason,evidence)
   SELECT gen_random_uuid()::text,id,version+1,'block',disposition,'blocked','legacy:unattributed','Existing intake suppression',jsonb_build_object('compatibility',true)
   FROM curation_entities WHERE id=target AND disposition IN ('pending','approved');
 END IF;
 -- UUID is an observation identity, not a fuzzy alias. Conflicting owners are retained.
 INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
 SELECT gen_random_uuid()::text,target,'comedian','entity','external_id','comedian-uuid:v1','global',input_uuid
 WHERE EXISTS(SELECT 1 FROM curation_entities WHERE id=target AND identity_scope='entity')
 ON CONFLICT(entity_kind,namespace,scope,value) DO NOTHING;
 IF coalesce(cardinality(matched),0)<=1 THEN
   FOR k IN SELECT * FROM jsonb_array_elements(input_keys) LOOP
     INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
     SELECT gen_random_uuid()::text,target,'comedian','entity','external_id',k->>'namespace',k->>'scope',k->>'value'
     WHERE EXISTS(SELECT 1 FROM curation_entities WHERE id=target AND identity_scope='entity')
     ON CONFLICT(entity_kind,namespace,scope,value) DO NOTHING;
   END LOOP;
 END IF;
 INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at)
 VALUES(gen_random_uuid()::text,target,'comedian-intake:v1',input_uuid,md5(jsonb_build_object('name',input_name,'evidence',evidence)::text),jsonb_build_object('name',input_name,'evidence',evidence),now()) ON CONFLICT DO NOTHING;
 RETURN target;
END $$;

-- Called only by authenticated review/admin services, before creating a public row.
-- A blocked identity must be restored separately; approval never implies restoration.
CREATE FUNCTION curation_approve_comedian(input_uuid text,input_name text,actor text,reason text,input_id integer DEFAULT NULL)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE target text; result record;
BEGIN
 PERFORM curation_lock_intake();
 IF nullif(btrim(actor),'') IS NULL OR nullif(btrim(reason),'') IS NULL THEN RAISE EXCEPTION 'Approval attribution required'; END IF;
 target:=curation_observe_comedian(input_uuid,input_name,jsonb_build_object('approvalRequestedBy',actor));
 IF input_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM curation_entities WHERE comedian_id=input_id) THEN
   UPDATE curation_entities SET comedian_id=input_id WHERE id=target AND comedian_id IS NULL;
 END IF;
 SELECT * INTO result FROM curation_comedian_policy(input_uuid,input_name,input_id);
 IF result.disposition='blocked' OR result.entity_id IS NULL OR result.entity_id<>target THEN
   RAISE EXCEPTION 'Identity is blocked or ambiguous; resolve curation first' USING ERRCODE='23514';
 END IF;
 IF input_id IS NOT NULL THEN
   UPDATE curation_entities SET comedian_id=input_id WHERE id=target AND (comedian_id IS NULL OR comedian_id=input_id);
   IF NOT FOUND THEN RAISE EXCEPTION 'Identity already has another public record'; END IF;
 END IF;
 INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
 SELECT gen_random_uuid()::text,id,version+1,'approve',disposition,'approved',actor,reason FROM curation_entities WHERE id=target AND disposition='pending';
 RETURN target;
END $$;

CREATE FUNCTION curation_comedian_row_keys(value jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
 SELECT coalesce(jsonb_agg(jsonb_build_object('namespace','provider:'||substr(encode(sha256(convert_to(to_jsonb(source)::text,'UTF8')),'hex'),1,24)||':v1','scope',source,'value',value->>field)), '[]'::jsonb)
 FROM (VALUES('bandsintown','bandsintown_id'),('songkick','songkick_id')) p(source,field)
 WHERE nullif(value->>field,'') IS NOT NULL
$$;
CREATE FUNCTION curation_guard_comedian_write() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE result record;
BEGIN
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
CREATE TRIGGER curation_comedian_write BEFORE INSERT OR UPDATE ON comedians FOR EACH ROW EXECUTE FUNCTION curation_guard_comedian_write();
CREATE FUNCTION curation_bind_comedian() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target text;
BEGIN
 SELECT entity_id INTO target FROM curation_comedian_policy(NEW.uuid,NEW.name);
 UPDATE curation_entities SET comedian_id=NEW.id WHERE id=target AND comedian_id IS NULL;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_comedian_bind AFTER INSERT ON comedians FOR EACH ROW EXECUTE FUNCTION curation_bind_comedian();
CREATE FUNCTION curation_guard_lineup_write() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record; result record;
BEGIN
 SELECT * INTO c FROM comedians WHERE uuid=NEW.comedian_id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT * INTO result FROM curation_comedian_policy(c.uuid,c.name,c.id);
 IF result.disposition<>'approved' OR result.comedian_id IS DISTINCT FROM c.id OR c.parent_comedian_id IS NOT NULL OR NOT c.visible
 OR EXISTS(SELECT 1 FROM shows s CROSS JOIN LATERAL curation_comedian_policy(NULL,s.name) p WHERE s.id=NEW.show_id AND p.disposition='blocked') THEN
   PERFORM curation_observe_comedian(c.uuid,c.name,jsonb_build_object('writer','lineup_items','row',to_jsonb(NEW)));
   RETURN NULL;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_lineup_write BEFORE INSERT OR UPDATE ON lineup_items FOR EACH ROW EXECUTE FUNCTION curation_guard_lineup_write();

CREATE FUNCTION curation_guard_candidate_write() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target text; result record;
BEGIN
 IF TG_OP='UPDATE' AND OLD.status IN ('rejected','accepted') AND NEW.status='pending' AND EXISTS(
 SELECT 1 FROM curation_entities e JOIN curation_identity_keys k ON k.entity_id=e.id
 WHERE (k.namespace='comedian-uuid:v1' OR k.namespace LIKE 'legacy:%:comedian_identity_candidates:v1') AND k.value=NEW.uuid AND e.disposition='pending'
 AND EXISTS(SELECT 1 FROM curation_decisions d WHERE d.entity_id=e.id AND d.version=e.version AND d.action='restore')) THEN RETURN NEW; END IF;
 target:=curation_observe_comedian(NEW.uuid,NEW.name,jsonb_build_object('writer','candidate','status',NEW.status));
 SELECT * INTO result FROM curation_comedian_policy(NEW.uuid,NEW.name,NEW.canonical_comedian_id);
 IF NEW.status='accepted' AND result.disposition<>'approved' THEN RAISE EXCEPTION 'Approve curation before accepting a candidate' USING ERRCODE='23514'; END IF;
 IF NEW.status='rejected' THEN
   INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
   SELECT gen_random_uuid()::text,id,version+1,'block',disposition,'blocked',coalesce(nullif(NEW.reviewed_by,''),'legacy:unattributed'),coalesce(nullif(NEW.reason,''),'Rejected identity') FROM curation_entities WHERE id=target AND disposition<>'blocked';
 ELSIF result.disposition='blocked' THEN
   IF TG_OP='INSERT' THEN RETURN NULL; END IF;
   NEW.status:='rejected';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_candidate_write BEFORE INSERT OR UPDATE ON comedian_identity_candidates FOR EACH ROW EXECUTE FUNCTION curation_guard_candidate_write();

CREATE FUNCTION curation_reopen_comedian(input_uuid text, actor text, reason text, expected_version integer)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE entity record;
BEGIN
 PERFORM curation_lock_intake();
 SELECT e.* INTO entity FROM curation_entities e JOIN curation_identity_keys k ON k.entity_id=e.id
 WHERE k.namespace='comedian-uuid:v1' AND k.scope='global' AND k.value=input_uuid;
 IF entity.id IS NULL OR expected_version IS NULL OR entity.version<>expected_version THEN
   RAISE EXCEPTION 'Curation changed after review; refresh before restoring' USING ERRCODE='40001';
 END IF;
 IF entity.disposition='approved' THEN
   INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
   VALUES(gen_random_uuid()::text,entity.id,entity.version+1,'block','approved','blocked',actor,reason);
   entity.version:=entity.version+1; entity.disposition:='blocked';
 END IF;
 IF entity.disposition='blocked' THEN
   INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
   VALUES(gen_random_uuid()::text,entity.id,entity.version+1,'restore','blocked','pending',actor,reason);
 END IF;
END $$;

-- New orphan-deny entries immediately become durable exact-name rules. Removing
-- the compatibility row alone cannot erase the decision; restore it explicitly.
CREATE FUNCTION curation_record_comedian_denial() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target text; normalized text;
BEGIN
 normalized:=curation_exact_name(NEW.name);
 SELECT entity_id INTO target FROM curation_identity_keys WHERE entity_kind='comedian' AND namespace='exact-name:v1' AND scope='global' AND value=normalized;
 IF target IS NULL THEN
  target:='comedian-name:'||md5(normalized);
  INSERT INTO curation_entities(id,kind,identity_scope,label) VALUES(target,'comedian','name',NEW.name);
  INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
  VALUES(gen_random_uuid()::text,target,'comedian','name','exact_name','exact-name:v1','global',normalized);
 END IF;
 INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
 SELECT gen_random_uuid()::text,id,version+1,'block',disposition,'blocked',coalesce(nullif(to_jsonb(NEW)->>'added_by',''),'legacy:unattributed'),coalesce(nullif(to_jsonb(NEW)->>'reason',''),'Orphan name denied')
 FROM curation_entities WHERE id=target AND disposition<>'blocked';
 RETURN NEW;
END $$;
CREATE TRIGGER curation_comedian_denial AFTER INSERT OR UPDATE ON comedian_deny_list FOR EACH ROW EXECUTE FUNCTION curation_record_comedian_denial();
