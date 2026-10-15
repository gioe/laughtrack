-- Occurrences, confirmed cross-source mappings and source-owned series are distinct.
CREATE TABLE curation_show_mappings (
 left_id text NOT NULL REFERENCES curation_entities(id) ON DELETE RESTRICT,
 right_id text NOT NULL REFERENCES curation_entities(id) ON DELETE RESTRICT,
 evidence jsonb NOT NULL,
 PRIMARY KEY(left_id,right_id), CHECK(left_id<right_id)
);
CREATE TABLE curation_show_series_members (
 series_id text NOT NULL REFERENCES curation_entities(id) ON DELETE RESTRICT,
 occurrence_id text NOT NULL REFERENCES curation_entities(id) ON DELETE RESTRICT,
 source_id integer NOT NULL REFERENCES scraping_sources(id) ON DELETE RESTRICT,
 PRIMARY KEY(series_id,occurrence_id)
);
CREATE FUNCTION curation_guard_show_edge() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM curation_lock_intake();
 IF TG_TABLE_NAME='curation_show_mappings' THEN
  IF (SELECT count(*) FROM curation_entities WHERE id IN (NEW.left_id,NEW.right_id) AND kind='show' AND identity_scope='entity')<>2 THEN RAISE EXCEPTION 'Mapping requires two occurrences'; END IF;
 ELSE
  IF NOT EXISTS(SELECT 1 FROM curation_entities WHERE id=NEW.occurrence_id AND kind='show' AND identity_scope='entity')
   OR NOT EXISTS(SELECT 1 FROM curation_entities e JOIN curation_identity_keys k ON k.entity_id=e.id WHERE e.id=NEW.series_id AND e.kind='show' AND e.identity_scope='series' AND k.namespace='show-series:v1' AND k.scope=NEW.source_id::text)
  THEN RAISE EXCEPTION 'Series membership requires an identified source-owned series'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_show_mapping_guard BEFORE INSERT ON curation_show_mappings FOR EACH ROW EXECUTE FUNCTION curation_guard_show_edge();
CREATE TRIGGER curation_show_series_guard BEFORE INSERT ON curation_show_series_members FOR EACH ROW EXECUTE FUNCTION curation_guard_show_edge();
CREATE TRIGGER curation_show_mapping_retained BEFORE UPDATE OR DELETE ON curation_show_mappings FOR EACH ROW EXECUTE FUNCTION curation_immutable_record();
CREATE TRIGGER curation_show_series_retained BEFORE UPDATE OR DELETE ON curation_show_series_members FOR EACH ROW EXECUTE FUNCTION curation_immutable_record();
CREATE FUNCTION curation_show_group(target text) RETURNS TABLE(id text) LANGUAGE sql STABLE AS $$
 WITH RECURSIVE members(id) AS (
 SELECT target UNION SELECT CASE WHEN m.left_id=g.id THEN m.right_id ELSE m.left_id END
 FROM members g JOIN curation_show_mappings m ON g.id IN(m.left_id,m.right_id)
 ) SELECT id FROM members
$$;
CREATE FUNCTION curation_show_keys(payload jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
DECLARE keys jsonb:='[]'; native text; url text; provider_id text; slot text;
BEGIN
 IF payload->>'id' ~ '^[0-9]+$' THEN keys:=keys||jsonb_build_array(jsonb_build_object('namespace','show-id:v1','scope','global','value',payload->>'id')); END IF;
 IF nullif(payload->>'provider_event_id','') IS NOT NULL THEN keys:=keys||jsonb_build_array(jsonb_build_object('namespace','show-provider-event:v1','scope','global','value',payload->>'provider_event_id')); END IF;
 native:=nullif(payload->>'source_performance_id','');
 IF native IS NOT NULL AND payload->>'club_id' IS NOT NULL THEN keys:=keys||jsonb_build_array(jsonb_build_object('namespace','show-performance:v1','scope',payload->>'club_id','value',native)); END IF;
 IF nullif(payload->>'event_key','') IS NOT NULL AND payload->>'source_id' ~ '^[0-9]+$' THEN keys:=keys||jsonb_build_array(jsonb_build_object('namespace','show-source-event:v1','scope',payload->>'source_id','value',payload->>'event_key')); END IF;
 -- Physical slots identify only legacy rows without a stronger native identity.
 IF native IS NULL AND payload->>'club_id' IS NOT NULL AND nullif(payload->>'date','') IS NOT NULL THEN
  slot:=jsonb_build_array(extract(epoch FROM (payload->>'date')::timestamptz),coalesce(payload->>'room',''))::text;
  keys:=keys||jsonb_build_array(jsonb_build_object('namespace','show-slot:v1','scope',payload->>'club_id','value',slot));
 END IF;
 url:=coalesce(payload->>'show_page_url',payload->>'url','');
 -- These providers identify a single event, not a calendar or recurring series.
 IF url ~* '^https?://([^/]+\.)?ticketmaster\.[^/]+/.*event/' THEN
  provider_id:=substring(url FROM '/event/([A-Za-z0-9]+)');
  IF provider_id IS NOT NULL THEN keys:=keys||jsonb_build_array(jsonb_build_object('namespace','show-ticketmaster:v1','scope','global','value',provider_id)); END IF;
 ELSIF url ~* '^https?://([^/]+\.)?eventbrite\.[^/]+/e/' THEN
  provider_id:=substring(url FROM '-tickets-([0-9]+)');
  IF provider_id IS NOT NULL THEN keys:=keys||jsonb_build_array(jsonb_build_object('namespace','show-eventbrite:v1','scope','global','value',provider_id)); END IF;
 END IF;
 RETURN keys;
END $$;
CREATE FUNCTION curation_show_matches(payload jsonb) RETURNS TABLE(id text) LANGUAGE sql STABLE AS $$
 WITH keys AS(SELECT * FROM jsonb_array_elements(curation_show_keys(payload)))
 SELECT e.id FROM curation_entities e WHERE e.kind='show' AND e.identity_scope='entity' AND (
 e.show_id::text=payload->>'id'
 OR EXISTS(SELECT 1 FROM curation_identity_keys k JOIN keys j ON k.namespace=j.value->>'namespace' AND k.scope=j.value->>'scope' AND k.value=j.value->>'value' WHERE k.entity_id=e.id)
 OR EXISTS(SELECT 1 FROM comedy_event_candidates c JOIN curation_identity_keys k ON k.entity_id=e.id
  WHERE c.source_id::text=payload->>'source_id' AND c.event_key=payload->>'event_key'
  AND ((k.namespace LIKE 'legacy:%:comedy_event_candidates:v1' AND k.value=c.id::text)
   OR (k.namespace LIKE 'legacy:%:event-key:v1' AND k.scope=c.source_id::text AND k.value=c.event_key)))
 OR EXISTS(SELECT 1 FROM shows s CROSS JOIN LATERAL jsonb_array_elements(curation_show_keys(to_jsonb(s))) sk
  JOIN keys j ON sk->>'namespace'=j.value->>'namespace' AND sk->>'scope'=j.value->>'scope' AND sk->>'value'=j.value->>'value' WHERE s.id=e.show_id)
 )
$$;
CREATE FUNCTION curation_show_policy(payload jsonb) RETURNS TABLE(allowed boolean,reason text,entity_id text) LANGUAGE plpgsql STABLE AS $$
DECLARE ids text[]; members text[]; chosen text;
BEGIN
 SELECT array_agg(id ORDER BY id) INTO ids FROM curation_show_matches(payload);
 chosen:=ids[1];
 IF chosen IS NULL THEN RETURN QUERY SELECT true,'unreviewed'::text,NULL::text; RETURN; END IF;
 SELECT array_agg(id) INTO members FROM curation_show_group(chosen);
 IF NOT ids <@ members THEN RETURN QUERY SELECT false,'ambiguous'::text,chosen; RETURN; END IF;
 IF EXISTS(SELECT 1 FROM curation_entities WHERE id=ANY(ids||members) AND disposition='blocked')
 OR EXISTS(SELECT 1 FROM curation_show_series_members m JOIN curation_entities e ON e.id=m.series_id WHERE m.occurrence_id=ANY(ids||members) AND e.disposition='blocked') THEN
  RETURN QUERY SELECT false,'blocked'::text,chosen; RETURN;
 END IF;
 IF EXISTS(SELECT 1 FROM curation_entities WHERE id=ANY(members) AND disposition='pending' AND version>0) THEN
  RETURN QUERY SELECT false,'review_required'::text,chosen; RETURN;
 END IF;
 RETURN QUERY SELECT true,'eligible_for_existing_screening'::text,chosen;
END $$;
CREATE FUNCTION curation_register_show_series(source integer,native_id text,label text) RETURNS text LANGUAGE plpgsql AS $$
DECLARE target text;
BEGIN
 PERFORM curation_lock_intake();
 IF NOT EXISTS(SELECT 1 FROM scraping_sources WHERE id=source) OR nullif(btrim(native_id),'') IS NULL OR nullif(btrim(label),'') IS NULL THEN RAISE EXCEPTION 'An identified source-owned series and label are required'; END IF;
 target:='show-series:'||md5(source::text||':'||native_id);
 INSERT INTO curation_entities(id,kind,identity_scope,label) VALUES(target,'show','series',label) ON CONFLICT(id) DO NOTHING;
 INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
 VALUES(gen_random_uuid()::text,target,'show','series','series_id','show-series:v1',source::text,native_id) ON CONFLICT DO NOTHING;
 RETURN target;
END $$;
CREATE FUNCTION curation_observe_show(payload jsonb,source text DEFAULT 'show-intake:v1') RETURNS text LANGUAGE plpgsql AS $$
DECLARE target text; result record; keys jsonb; key jsonb; series text; public_id integer;
BEGIN
 PERFORM curation_lock_intake();
 keys:=curation_show_keys(payload);
 IF keys='[]'::jsonb THEN RAISE EXCEPTION 'Show identity unavailable'; END IF;
 SELECT * INTO result FROM curation_show_policy(payload);
 target:=result.entity_id;
 IF target IS NULL THEN
  target:='show-intake:'||md5(keys::text);
  SELECT id INTO public_id FROM shows WHERE id::text=payload->>'id';
  INSERT INTO curation_entities(id,kind,label,show_id) VALUES(target,'show',coalesce(nullif(payload->>'name',''),'Unresolved show'),public_id) ON CONFLICT DO NOTHING;
 END IF;
 IF result.reason<>'ambiguous' THEN
  FOR key IN SELECT * FROM jsonb_array_elements(keys) LOOP
   INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
   VALUES(gen_random_uuid()::text,target,'show','entity','external_id',key->>'namespace',key->>'scope',key->>'value') ON CONFLICT DO NOTHING;
  END LOOP;
  IF nullif(payload->>'series_id','') IS NOT NULL THEN
   series:=curation_register_show_series((payload->>'source_id')::integer,payload->>'series_id',coalesce(nullif(payload->>'series_name',''),payload->>'series_id'));
   INSERT INTO curation_show_series_members(series_id,occurrence_id,source_id) VALUES(series,target,(payload->>'source_id')::integer) ON CONFLICT DO NOTHING;
  END IF;
 END IF;
 INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at)
 VALUES(gen_random_uuid()::text,target,source,target,md5(payload::text),jsonb_build_object('show',payload,'policy',result.reason),now()) ON CONFLICT DO NOTHING;
 RETURN target;
END $$;
CREATE FUNCTION curation_show_affected(target text) RETURNS TABLE(id integer) LANGUAGE sql STABLE AS $$
 WITH seeds AS(SELECT target AS id UNION SELECT occurrence_id FROM curation_show_series_members WHERE series_id=target),
 members AS(SELECT DISTINCT g.id FROM seeds CROSS JOIN LATERAL curation_show_group(seeds.id) g)
 SELECT DISTINCT e.show_id FROM curation_entities e JOIN members m ON m.id=e.id WHERE e.show_id IS NOT NULL
$$;
CREATE FUNCTION curation_project_show_block() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.entity_id IS NOT NULL AND NEW.action='block' AND EXISTS(SELECT 1 FROM curation_entities WHERE id=NEW.entity_id AND kind='show') THEN
  UPDATE shows SET visible=false WHERE id IN(SELECT id FROM curation_show_affected(NEW.entity_id));
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER zz_curation_show_block AFTER INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_project_show_block();
CREATE FUNCTION curation_guard_show_write() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE payload jsonb; result record;
BEGIN
 IF TG_OP='UPDATE' THEN
  PERFORM curation_observe_show(to_jsonb(OLD));
  IF NOT NEW.visible AND (to_jsonb(NEW)-'visible') IS NOT DISTINCT FROM (to_jsonb(OLD)-'visible') THEN RETURN NEW; END IF;
 END IF;
 payload:=to_jsonb(NEW);
 IF TG_OP='INSERT' THEN payload:=payload-'id'; END IF;
 PERFORM curation_observe_show(payload);
 SELECT * INTO result FROM curation_show_policy(payload||jsonb_build_object('id',NEW.id));
 IF NOT result.allowed THEN
  IF TG_OP='UPDATE' THEN RETURN OLD; ELSE RETURN NULL; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_show_write BEFORE INSERT OR UPDATE ON shows FOR EACH ROW EXECUTE FUNCTION curation_guard_show_write();
CREATE FUNCTION curation_bind_show() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target text;
BEGIN
 SELECT entity_id INTO target FROM curation_show_policy(to_jsonb(NEW)-'id');
 UPDATE curation_entities SET show_id=NEW.id WHERE id=target AND show_id IS NULL;
 PERFORM curation_observe_show(to_jsonb(NEW));
 RETURN NEW;
END $$;
CREATE TRIGGER curation_show_bind AFTER INSERT ON shows FOR EACH ROW EXECUTE FUNCTION curation_bind_show();
CREATE FUNCTION curation_retain_show() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM curation_observe_show(to_jsonb(OLD));
 IF NOT OLD.visible OR NOT (SELECT allowed FROM curation_show_policy(to_jsonb(OLD))) THEN RETURN NULL; END IF;
 RETURN OLD;
END $$;
CREATE TRIGGER curation_show_delete BEFORE DELETE ON shows FOR EACH ROW EXECUTE FUNCTION curation_retain_show();
CREATE FUNCTION curation_stage_show() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidate record;
BEGIN
 SELECT * INTO candidate FROM comedy_event_candidates WHERE id=NEW.candidate_id;
 PERFORM curation_observe_show(NEW.payload||jsonb_build_object('source_id',candidate.source_id,'event_key',candidate.event_key,'club_id',candidate.club_id),'eligibility');
 RETURN NEW;
END $$;
CREATE TRIGGER curation_show_stage AFTER INSERT ON comedy_event_decisions FOR EACH ROW EXECUTE FUNCTION curation_stage_show();
CREATE FUNCTION curation_map_show_publication() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidate record; payload jsonb; public_target text; candidate_target text;
BEGIN
 SELECT * INTO candidate FROM comedy_event_candidates WHERE id=NEW.candidate_id;
 SELECT d.payload INTO payload FROM comedy_event_decisions d WHERE d.id=NEW.decision_id;
 candidate_target:=curation_observe_show(payload||jsonb_build_object('source_id',candidate.source_id,'event_key',candidate.event_key,'club_id',candidate.club_id),'eligibility');
 SELECT to_jsonb(s) INTO payload FROM shows s WHERE s.id=NEW.show_id;
 public_target:=curation_observe_show(payload);
 IF candidate_target<>public_target THEN
  INSERT INTO curation_show_mappings(left_id,right_id,evidence) VALUES(least(candidate_target,public_target),greatest(candidate_target,public_target),jsonb_build_object('candidate_id',NEW.candidate_id,'show_id',NEW.show_id,'decision_id',NEW.decision_id)) ON CONFLICT DO NOTHING;
 END IF;
 IF NOT (SELECT allowed FROM curation_show_policy(payload)) THEN UPDATE shows SET visible=false WHERE id=NEW.show_id; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_show_publication AFTER INSERT OR UPDATE ON comedy_event_publications FOR EACH ROW EXECUTE FUNCTION curation_map_show_publication();
-- Existing review workers keep their evidence/source/version fences. Only an
-- applied rejection becomes a durable occurrence block; approval never restores.
CREATE FUNCTION curation_review_show() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidate record; payload jsonb; target text;
BEGIN
 SELECT * INTO candidate FROM comedy_event_candidates WHERE id=NEW.candidate_id;
 SELECT d.payload INTO payload FROM comedy_event_decisions d WHERE id=NEW.decision_id;
 target:=curation_observe_show(payload||jsonb_build_object('source_id',candidate.source_id,'event_key',candidate.event_key,'club_id',candidate.club_id),'event-review');
 IF NEW.action='reject' THEN
  INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
  SELECT gen_random_uuid()::text,id,version+1,'block',disposition,'blocked',NEW.actor,NEW.reason FROM curation_entities WHERE id=target AND disposition<>'blocked';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_show_review AFTER INSERT ON comedy_event_reviews FOR EACH ROW EXECUTE FUNCTION curation_review_show();
-- Intake locks precede source/candidate row locks in application code as well.
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON comedy_event_candidates FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT ON comedy_event_decisions FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT ON comedy_event_reviews FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE ON comedy_event_publications FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();

CREATE FUNCTION curation_project_show_edge() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='curation_show_mappings' THEN
  UPDATE shows s SET visible=false WHERE s.visible AND s.id IN(SELECT id FROM curation_show_affected(NEW.left_id)) AND NOT (SELECT allowed FROM curation_show_policy(to_jsonb(s)));
 ELSE
  UPDATE shows s SET visible=false WHERE s.visible AND s.id IN(SELECT id FROM curation_show_affected(NEW.occurrence_id)) AND NOT (SELECT allowed FROM curation_show_policy(to_jsonb(s)));
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_show_mapping_projection AFTER INSERT ON curation_show_mappings FOR EACH ROW EXECUTE FUNCTION curation_project_show_edge();
CREATE TRIGGER curation_show_series_projection AFTER INSERT ON curation_show_series_members FOR EACH ROW EXECUTE FUNCTION curation_project_show_edge();
-- Preserve already-confirmed publication links; this does not reclassify events.
DO $$ DECLARE publication record; BEGIN
 FOR publication IN SELECT * FROM comedy_event_publications LOOP
  UPDATE comedy_event_publications SET published_at=published_at WHERE candidate_id=publication.candidate_id AND decision_id=publication.decision_id AND show_id=publication.show_id;
 END LOOP;
END $$;

CREATE TRIGGER aa_curation_show_delete_lock BEFORE DELETE ON shows FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();

-- Worker-applied suppression must invalidate cached public pages as well.
CREATE TABLE show_publication_revision(id integer PRIMARY KEY CHECK(id=1), revision bigint NOT NULL DEFAULT 0);
INSERT INTO show_publication_revision(id) VALUES(1);
CREATE FUNCTION bump_show_publication_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN UPDATE show_publication_revision SET revision=revision+1 WHERE id=1; RETURN NEW; END $$;
CREATE TRIGGER show_publication_cache AFTER UPDATE OF visible,is_cancelled ON shows FOR EACH ROW
 WHEN (OLD.visible IS DISTINCT FROM NEW.visible OR OLD.is_cancelled IS DISTINCT FROM NEW.is_cancelled)
 EXECUTE FUNCTION bump_show_publication_revision();
