-- Pending podcast rows are staging metadata, never public or episode-admissible.
-- URL normalization deliberately preserves scheme, path case, query and trailing slash.
CREATE FUNCTION curation_feed_url(value text) RETURNS text LANGUAGE plpgsql IMMUTABLE STRICT AS $$
DECLARE parts text[];
BEGIN
 parts:=regexp_match(btrim(value),'^(https?)://([^/?#]+)([^#]*)(#.*)?$','i');
 IF parts IS NULL OR parts[2] LIKE '%@%' THEN RETURN NULL; END IF;
 RETURN lower(parts[1])||'://'||regexp_replace(lower(parts[2]),CASE WHEN lower(parts[1])='https' THEN ':443$' ELSE ':80$' END,'')||CASE WHEN coalesce(parts[3],'')='' THEN '/' WHEN left(parts[3],1)='?' THEN '/'||parts[3] ELSE parts[3] END;
END $$;
CREATE INDEX curation_podcast_legacy_feed ON curation_identity_keys(curation_feed_url(value)) WHERE entity_kind='podcast' AND namespace='podcast-feed:exact:v1';
CREATE INDEX curation_podcast_active_feed_denial ON podcast_deny_list(curation_feed_url(feed_url)) WHERE restored_at IS NULL;
CREATE FUNCTION curation_podcast_keys(payload jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE WHEN payload->>'id' ~ '^[0-9]+$' THEN jsonb_build_array(jsonb_build_object('namespace','podcast-id:v1','scope','global','value',payload->>'id')) ELSE '[]'::jsonb END
 || CASE WHEN nullif(payload->>'source','') IS NOT NULL AND nullif(payload->>'source_podcast_id','') IS NOT NULL THEN jsonb_build_array(jsonb_build_object('namespace','podcast-provider:v1','scope',payload->>'source','value',payload->>'source_podcast_id')) ELSE '[]'::jsonb END
 || CASE WHEN curation_feed_url(payload->>'feed_url') IS NOT NULL THEN jsonb_build_array(jsonb_build_object('namespace','podcast-feed:v1','scope','global','value',curation_feed_url(payload->>'feed_url'))) ELSE '[]'::jsonb END
 || CASE WHEN nullif(payload->'external_ids'->>'podcast_index_feed_id','') IS NOT NULL THEN jsonb_build_array(jsonb_build_object('namespace','podcast-provider:v1','scope','podcast_index','value',payload->'external_ids'->>'podcast_index_feed_id')) ELSE '[]'::jsonb END
 || CASE WHEN nullif(payload->'external_ids'->>'itunes_collection_id','') IS NOT NULL THEN jsonb_build_array(jsonb_build_object('namespace','podcast-provider:v1','scope','itunes','value',payload->'external_ids'->>'itunes_collection_id')) ELSE '[]'::jsonb END
$$;
CREATE FUNCTION curation_podcast_policy(payload jsonb) RETURNS TABLE(disposition text,entity_id text,podcast_id integer) LANGUAGE plpgsql STABLE AS $$
DECLARE ids text[]; keys jsonb;
BEGIN
 keys:=curation_podcast_keys(payload);

 SELECT array_agg(DISTINCT id) INTO ids FROM (
 SELECT e.id FROM curation_entities e WHERE e.kind='podcast' AND e.podcast_id=CASE WHEN payload->>'id' ~ '^[0-9]+$' THEN (payload->>'id')::int END
 UNION SELECT k.entity_id FROM jsonb_array_elements(keys) j JOIN curation_identity_keys k ON k.entity_kind='podcast' AND k.namespace=j->>'namespace' AND k.scope=j->>'scope' AND k.value=j->>'value'
 UNION SELECT k.entity_id FROM jsonb_array_elements(keys) j JOIN curation_identity_keys k ON k.entity_kind='podcast' AND k.namespace LIKE 'provider:%:v1' AND j->>'namespace'='podcast-provider:v1' AND k.scope=j->>'scope' AND k.value=j->>'value'
 UNION SELECT k.entity_id FROM jsonb_array_elements(keys) j JOIN curation_identity_keys k ON k.entity_kind='podcast' AND k.namespace='podcast-feed:exact:v1' AND j->>'namespace'='podcast-feed:v1' AND curation_feed_url(k.value)=j->>'value'
 ) matched;
 IF EXISTS(SELECT 1 FROM curation_entities e WHERE e.id=ANY(ids) AND e.disposition='blocked') THEN
 RETURN QUERY SELECT 'blocked'::text,CASE WHEN cardinality(ids)=1 THEN ids[1] END,NULL::int; RETURN;
 END IF;
 -- Compatibility rows are captured transactionally by triggers below. Before
 -- rollout capture, consult their original stable keys too (no title matching).
 IF EXISTS(SELECT 1 FROM podcast_deny_list d WHERE d.restored_at IS NULL AND (
 d.podcast_id=CASE WHEN payload->>'id' ~ '^[0-9]+$' THEN (payload->>'id')::int END OR
 (d.source=payload->>'source' AND d.source_podcast_id=payload->>'source_podcast_id') OR
 (curation_feed_url(d.feed_url)=curation_feed_url(payload->>'feed_url') AND curation_feed_url(payload->>'feed_url') IS NOT NULL))) THEN
 RETURN QUERY SELECT 'blocked'::text,CASE WHEN cardinality(ids)=1 THEN ids[1] END,NULL::int; RETURN;
 END IF;
 IF cardinality(ids)>1 THEN RETURN QUERY SELECT 'ambiguous'::text,NULL::text,NULL::int; RETURN; END IF;
 RETURN QUERY SELECT coalesce(e.disposition,'pending'),e.id,e.podcast_id FROM (SELECT 1) dummy LEFT JOIN curation_entities e ON e.id=ids[1];
END $$;
CREATE FUNCTION curation_observe_podcast(payload jsonb) RETURNS text LANGUAGE plpgsql AS $$
DECLARE result record; target text; key jsonb;
BEGIN
 PERFORM curation_lock_intake();
 SELECT * INTO result FROM curation_podcast_policy(payload);
 IF result.disposition='ambiguous' OR (result.disposition='blocked' AND result.entity_id IS NULL) THEN RETURN NULL; END IF;
 target:=result.entity_id;
 IF target IS NULL THEN
 target:='podcast-intake:'||md5(curation_podcast_keys(payload)::text);
 INSERT INTO curation_entities(id,kind,label) VALUES(target,'podcast',coalesce(nullif(payload->>'title',''),'Unresolved podcast')) ON CONFLICT DO NOTHING;
 END IF;
 FOR key IN SELECT * FROM jsonb_array_elements(curation_podcast_keys(payload)) LOOP
 INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
 VALUES(gen_random_uuid()::text,target,'podcast','entity','external_id',key->>'namespace',key->>'scope',key->>'value') ON CONFLICT DO NOTHING;
 END LOOP;
 IF payload->>'id' ~ '^[0-9]+$' THEN
 UPDATE curation_entities SET podcast_id=(payload->>'id')::int WHERE id=target AND podcast_id IS NULL AND EXISTS(SELECT 1 FROM podcasts WHERE id=(payload->>'id')::int);
 END IF;
 INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at)
 VALUES(gen_random_uuid()::text,target,'podcast-intake:v1',target,md5(payload::text),jsonb_build_object('podcast',payload),now()) ON CONFLICT DO NOTHING;
 RETURN target;
END $$;
CREATE FUNCTION curation_podcast_allowed(public_id integer) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT coalesce((SELECT q.disposition='approved' AND q.podcast_id=p.id FROM podcasts p CROSS JOIN LATERAL curation_podcast_policy(to_jsonb(p)) q WHERE p.id=public_id),false)
$$;
CREATE FUNCTION curation_guard_podcast() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE result record; payload jsonb;
BEGIN
 payload:=to_jsonb(NEW); IF TG_OP='INSERT' THEN payload:=payload-'id'; END IF;
 IF TG_OP='UPDATE' THEN PERFORM curation_observe_podcast(to_jsonb(OLD)); END IF;
 SELECT * INTO result FROM curation_podcast_policy(payload);
 IF result.disposition IN ('blocked','ambiguous') THEN RAISE EXCEPTION 'Podcast intake held: %',result.disposition USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' AND result.podcast_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM podcasts WHERE id=result.podcast_id AND source=NEW.source AND source_podcast_id=NEW.source_podcast_id) THEN
 RAISE EXCEPTION 'Podcast identity already exists: %',result.podcast_id USING ERRCODE='23514'; END IF;
 PERFORM curation_observe_podcast(payload);
 RETURN NEW;
END $$;
CREATE FUNCTION curation_bind_podcast() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN PERFORM curation_observe_podcast(to_jsonb(NEW)); RETURN NEW; END $$;
CREATE FUNCTION curation_guard_podcast_episode() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT curation_podcast_allowed(NEW.podcast_id) THEN RAISE EXCEPTION 'Podcast episode intake held pending approval' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON podcasts FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE ON podcast_episodes FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON podcast_deny_list FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER curation_podcast_guard BEFORE INSERT OR UPDATE ON podcasts FOR EACH ROW EXECUTE FUNCTION curation_guard_podcast();
CREATE TRIGGER curation_podcast_bind AFTER INSERT OR UPDATE ON podcasts FOR EACH ROW EXECUTE FUNCTION curation_bind_podcast();
CREATE TRIGGER curation_podcast_episode BEFORE INSERT OR UPDATE ON podcast_episodes FOR EACH ROW EXECUTE FUNCTION curation_guard_podcast_episode();
-- Explicit verified redirects/aliases only. Merely fetching a redirect is not
-- proof: generic landing pages and hijacked feeds must never merge identities.
CREATE FUNCTION curation_verify_podcast_feed(target text,feed text,actor text,reason text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE owner text; normalized text; policy record;
BEGIN
 PERFORM curation_lock_intake(); normalized:=curation_feed_url(feed);
 IF normalized IS NULL OR nullif(btrim(actor),'') IS NULL OR nullif(btrim(reason),'') IS NULL THEN RAISE EXCEPTION 'Verified feed requires URL, actor and evidence'; END IF;
 IF NOT EXISTS(SELECT 1 FROM curation_entities WHERE id=target AND kind='podcast') THEN RAISE EXCEPTION 'Unknown podcast'; END IF;
 SELECT * INTO policy FROM curation_podcast_policy(jsonb_build_object('feed_url',feed));
 IF policy.disposition='ambiguous' OR (policy.disposition='blocked' AND policy.entity_id IS NULL) THEN RAISE EXCEPTION 'Ambiguous feed identity'; END IF;
 owner:=policy.entity_id;
 IF owner IS NOT NULL AND owner<>target THEN RAISE EXCEPTION 'Feed belongs to another identity'; END IF;
 INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES(gen_random_uuid()::text,target,'podcast','entity','feed_url','podcast-feed:v1','global',normalized) ON CONFLICT DO NOTHING;
 INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at) VALUES(gen_random_uuid()::text,target,'verified-feed-alias',normalized,md5(actor||reason||normalized),jsonb_build_object('actor',actor,'reason',reason,'feed_url',feed),now()) ON CONFLICT DO NOTHING;
 UPDATE show_publication_revision SET revision=revision+1 WHERE id=1;
END $$;
-- Capture every extant identity as pending unless already reconciled. No implicit
-- approval from accepted host links, which are a separate review decision.
INSERT INTO curation_entities(id,kind,label,podcast_id)
 SELECT 'podcast-intake:id:'||p.id,'podcast',coalesce(nullif(p.title,''),'Unresolved podcast'),p.id FROM podcasts p
 WHERE NOT EXISTS(SELECT 1 FROM curation_entities e WHERE e.podcast_id=p.id) ON CONFLICT DO NOTHING;
INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
 SELECT gen_random_uuid()::text,e.id,'podcast','entity','external_id',k->>'namespace',k->>'scope',k->>'value'
 FROM podcasts p JOIN curation_entities e ON e.podcast_id=p.id CROSS JOIN LATERAL jsonb_array_elements(curation_podcast_keys(to_jsonb(p))) k
 ORDER BY p.id ON CONFLICT DO NOTHING;
INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at)
 SELECT gen_random_uuid()::text,e.id,'podcast-intake:v1',e.id,md5(to_jsonb(p)::text),jsonb_build_object('podcast',to_jsonb(p)),now()
 FROM podcasts p JOIN curation_entities e ON e.podcast_id=p.id ON CONFLICT DO NOTHING;
ANALYZE curation_identity_keys;
ANALYZE curation_entities;
CREATE FUNCTION curation_project_podcast_decision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM curation_entities WHERE id=NEW.entity_id AND kind='podcast') THEN
  IF NEW.action='restore' THEN
   UPDATE podcast_deny_list d SET restored_at=now(),restored_by=NEW.actor WHERE restored_at IS NULL AND (
    d.podcast_id=(SELECT podcast_id FROM curation_entities WHERE id=NEW.entity_id) OR EXISTS(
    SELECT 1 FROM jsonb_array_elements(curation_podcast_keys(to_jsonb(d)||jsonb_build_object('id',d.podcast_id))) dk JOIN curation_identity_keys k ON k.namespace=dk->>'namespace' AND k.scope=dk->>'scope' AND k.value=dk->>'value' WHERE k.entity_id=NEW.entity_id));
  END IF;
  UPDATE show_publication_revision SET revision=revision+1 WHERE id=1;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER zz_curation_podcast_decision AFTER INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_project_podcast_decision();
CREATE FUNCTION curation_capture_podcast_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN PERFORM curation_observe_podcast(to_jsonb(OLD)); RETURN OLD; END $$;
CREATE TRIGGER curation_podcast_delete BEFORE DELETE ON podcasts FOR EACH ROW EXECUTE FUNCTION curation_capture_podcast_delete();

CREATE FUNCTION curation_sync_podcast_denial() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE payload jsonb; target text; owner record; key jsonb; restoring boolean; restore_transition boolean:=false;
BEGIN
 payload:=CASE WHEN TG_OP='DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
 restoring:=payload->>'restored_at' IS NOT NULL;
 IF TG_OP='UPDATE' THEN restore_transition:=OLD.restored_at IS NULL AND NEW.restored_at IS NOT NULL; END IF;
 SELECT k.entity_id INTO target FROM curation_identity_keys k JOIN jsonb_array_elements(curation_podcast_keys(payload||jsonb_build_object('id',payload->>'podcast_id'))) j ON k.entity_kind='podcast' AND k.namespace=j->>'namespace' AND k.scope=j->>'scope' AND k.value=j->>'value' ORDER BY k.entity_id LIMIT 1;
 target:=coalesce(target,'podcast-denial:'||(payload->>'id'));
 INSERT INTO curation_entities(id,kind,label) VALUES(target,'podcast',coalesce(payload->>'feed_url','Denied podcast')) ON CONFLICT DO NOTHING;
 FOR key IN SELECT * FROM jsonb_array_elements(curation_podcast_keys(payload||jsonb_build_object('id',payload->>'podcast_id'))) LOOP
 INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES(gen_random_uuid()::text,target,'podcast','entity','external_id',key->>'namespace',key->>'scope',key->>'value') ON CONFLICT DO NOTHING;
 END LOOP;
 FOR owner IN SELECT DISTINCT e.* FROM curation_entities e JOIN curation_identity_keys k ON k.entity_id=e.id JOIN jsonb_array_elements(curation_podcast_keys(payload||jsonb_build_object('id',payload->>'podcast_id'))) j ON k.entity_kind='podcast' AND k.namespace=j->>'namespace' AND k.scope=j->>'scope' AND k.value=j->>'value' LOOP
  IF (restore_transition AND owner.disposition='blocked') OR (NOT restoring AND owner.disposition<>'blocked') THEN
   INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason,evidence)
   VALUES(gen_random_uuid()::text,owner.id,owner.version+1,CASE WHEN restoring THEN 'restore' ELSE 'block' END,owner.disposition,CASE WHEN restoring THEN 'pending' ELSE 'blocked' END,coalesce(nullif(payload->>'restored_by',''),nullif(payload->>'denied_by',''),'legacy:unattributed'),coalesce(nullif(payload->>'reason',''),'Legacy podcast denial'),payload);
  END IF;
 END LOOP;
 UPDATE show_publication_revision SET revision=revision+1 WHERE id=1;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
END $$;
CREATE TRIGGER curation_podcast_denial AFTER INSERT OR UPDATE ON podcast_deny_list FOR EACH ROW EXECUTE FUNCTION curation_sync_podcast_denial();
CREATE TRIGGER curation_podcast_denial_delete BEFORE DELETE ON podcast_deny_list FOR EACH ROW EXECUTE FUNCTION curation_sync_podcast_denial();
-- Fire compatibility capture without changing historical timestamps or actors.
UPDATE podcast_deny_list SET id=id;


