-- Club intake is separate from visibility, operating status and scrape policy.
CREATE FUNCTION curation_club_keys(payload jsonb, supplied jsonb DEFAULT '[]') RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
 SELECT supplied || CASE WHEN payload->>'id' ~ '^[0-9]+$' THEN jsonb_build_array(jsonb_build_object('namespace','club-id:v1','scope','global','value',payload->>'id')) ELSE '[]'::jsonb END || CASE WHEN nullif(payload->>'google_place_id','') IS NOT NULL THEN jsonb_build_array(jsonb_build_object('namespace','google-place:v1','scope','global','value',payload->>'google_place_id')) ELSE '[]'::jsonb END
 || CASE WHEN nullif(btrim(payload->>'address'),'') IS NOT NULL AND nullif(btrim(payload->>'name'),'') IS NOT NULL
 THEN jsonb_build_array(jsonb_build_object('namespace','club-location:v1','scope',jsonb_build_array(curation_exact_name(payload->>'address'),curation_exact_name(payload->>'city'),curation_exact_name(payload->>'state'),curation_exact_name(payload->>'country'))::text,'value',curation_exact_name(payload->>'name'))) ELSE '[]'::jsonb END
$$;
CREATE FUNCTION curation_club_source_keys(payload jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
 SELECT coalesce(jsonb_agg(jsonb_build_object('namespace','club-provider:'||field||':v1','scope','global','value',payload->>field)),'[]'::jsonb)
 FROM unnest(ARRAY['seatengine_id','seatengine_v3_id','ticketmaster_id','eventbrite_id']) field
 WHERE nullif(payload->>field,'') IS NOT NULL
 -- Organizer IDs are not venue IDs. Eventbrite callers must explicitly supply
 -- eventbrite_venue_id rather than borrowing an organizer scraping-source ID.
 AND field<>'eventbrite_id'
$$;
-- Missing optional geography is not evidence of a different venue. Match the
-- same exact address conservatively; explicit conflicts remain separate and
-- multiple compatible identities keep policy pending.
CREATE FUNCTION curation_club_location_compatible(saved text,candidate text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT saved::jsonb->>0=candidate::jsonb->>0 AND NOT EXISTS(
  SELECT 1 FROM generate_series(1,3) i WHERE saved::jsonb->>i IS NOT NULL
  AND candidate::jsonb->>i IS NOT NULL AND saved::jsonb->>i<>candidate::jsonb->>i
 )
$$;
CREATE FUNCTION curation_club_matches(payload jsonb, supplied jsonb DEFAULT '[]') RETURNS TABLE(id text) LANGUAGE sql STABLE AS $$
 WITH keys AS (SELECT * FROM jsonb_array_elements(curation_club_keys(payload,supplied))),
 matched_clubs AS (
 SELECT c.id FROM clubs c WHERE c.id::text=payload->>'id'
 OR (nullif(payload->>'google_place_id','') IS NOT NULL AND c.google_place_id=payload->>'google_place_id')
 OR (nullif(payload->>'address','') IS NOT NULL AND curation_exact_name(c.address)=curation_exact_name(payload->>'address') AND curation_exact_name(c.name)=curation_exact_name(payload->>'name') AND (nullif(payload->>'city','') IS NULL OR c.city IS NULL OR curation_exact_name(c.city)=curation_exact_name(payload->>'city')) AND (nullif(payload->>'state','') IS NULL OR c.state IS NULL OR curation_exact_name(c.state)=curation_exact_name(payload->>'state')) AND (nullif(payload->>'country','') IS NULL OR c.country IS NULL OR curation_exact_name(c.country)=curation_exact_name(payload->>'country')))
 OR EXISTS(SELECT 1 FROM club_aliases a WHERE a.club_id=c.id AND a.verified
  AND curation_exact_name(a.alias_name)=curation_exact_name(payload->>'name') AND (nullif(payload->>'country','') IS NULL OR c.country IS NULL OR curation_exact_name(c.country)=curation_exact_name(payload->>'country'))
  AND curation_exact_name(a.city)=curation_exact_name(payload->>'city') AND curation_exact_name(a.state)=curation_exact_name(payload->>'state')
  AND (nullif(payload->>'address','') IS NULL OR curation_exact_name(c.address)=curation_exact_name(payload->>'address')))
 OR EXISTS(SELECT 1 FROM scraping_sources s CROSS JOIN LATERAL jsonb_array_elements(curation_club_source_keys(to_jsonb(s))) sk
  JOIN keys k ON sk->>'namespace'=k.value->>'namespace' AND sk->>'scope'=k.value->>'scope' AND sk->>'value'=k.value->>'value' WHERE s.club_id=c.id)
 )
 SELECT e.id FROM curation_entities e WHERE e.kind='club' AND e.identity_scope='entity' AND
 (e.club_id IN (SELECT id FROM matched_clubs) OR EXISTS(SELECT 1 FROM curation_identity_keys k JOIN keys j ON k.namespace=j.value->>'namespace' AND k.value=j.value->>'value' AND (k.scope=j.value->>'scope' OR (k.namespace='club-location:v1' AND curation_club_location_compatible(k.scope,j.value->>'scope'))) WHERE k.entity_id=e.id))
$$;
CREATE FUNCTION curation_club_policy(payload jsonb, supplied jsonb DEFAULT '[]') RETURNS TABLE(disposition text,entity_id text,club_id integer) LANGUAGE plpgsql STABLE AS $$
DECLARE ids text[]; chosen text;
BEGIN
 SELECT array_agg(m.id) INTO ids FROM curation_club_matches(payload,supplied) m;
 IF EXISTS(SELECT 1 FROM curation_entities e WHERE e.id=ANY(ids) AND e.disposition='blocked')
 OR EXISTS(SELECT 1 FROM venue_deny_list d WHERE d.google_place_id=payload->>'google_place_id' OR EXISTS(
 SELECT 1 FROM curation_identity_keys k WHERE k.entity_id=ANY(ids) AND k.namespace='google-place:v1' AND k.value=d.google_place_id)) THEN
 RETURN QUERY SELECT 'blocked'::text,coalesce((SELECT e.id FROM curation_entities e WHERE e.id=ANY(ids) AND e.disposition='blocked' ORDER BY e.id LIMIT 1),ids[1]),NULL::int; RETURN;
 END IF;
 IF cardinality(ids)=1 THEN chosen:=ids[1]; END IF;
 RETURN QUERY SELECT CASE WHEN chosen IS NOT NULL AND e.disposition='approved' THEN 'approved' ELSE 'pending' END,chosen,e.club_id
 FROM (SELECT 1) dummy LEFT JOIN curation_entities e ON e.id=chosen;
END $$;
CREATE FUNCTION curation_observe_club(payload jsonb,supplied jsonb DEFAULT '[]',source text DEFAULT 'club-intake:v1') RETURNS text LANGUAGE plpgsql AS $$
DECLARE result record; target text; key jsonb; keys jsonb; fingerprint text;
BEGIN
 PERFORM curation_lock_intake();
 keys:=curation_club_keys(payload,supplied);
 SELECT * INTO result FROM curation_club_policy(payload,supplied);
 target:=result.entity_id;
 fingerprint:=md5(payload::text||keys::text);
 IF target IS NULL THEN
  -- Stable unresolved candidate, not a name-only identity merge. Location or
  -- provider keys define identity; incomplete inputs remain review-only.
  target:='club-intake:'||md5(CASE WHEN keys<>'[]'::jsonb THEN keys::text ELSE payload::text END);
  INSERT INTO curation_entities(id,kind,label,club_id)
  VALUES(target,'club',coalesce(nullif(payload->>'name',''),'Unresolved venue'),
   CASE WHEN payload->>'id' ~ '^[0-9]+$' AND NOT EXISTS(SELECT 1 FROM curation_entities WHERE club_id=(payload->>'id')::integer) THEN (payload->>'id')::integer END)
  ON CONFLICT(id) DO NOTHING;
 END IF;
 -- Conflicting keys are never reassigned. Their multiple owners keep admission held.
 FOR key IN SELECT * FROM jsonb_array_elements(keys) LOOP
  INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value)
  VALUES(gen_random_uuid()::text,target,'club','entity','external_id',key->>'namespace',key->>'scope',key->>'value')
  ON CONFLICT(entity_kind,namespace,scope,value) DO NOTHING;
 END LOOP;
 IF result.disposition='blocked' THEN
  INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
  SELECT gen_random_uuid()::text,id,version+1,'block',disposition,'blocked','legacy:unattributed','Existing venue denial' FROM curation_entities WHERE id=target AND disposition<>'blocked';
 END IF;
 INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at)
 VALUES(gen_random_uuid()::text,target,source,target,fingerprint,jsonb_build_object('venue',payload,'keys',keys),now()) ON CONFLICT DO NOTHING;
 RETURN target;
END $$;
CREATE FUNCTION curation_approve_club(payload jsonb,actor text,reason text) RETURNS text LANGUAGE plpgsql AS $$
DECLARE target text; result record;
BEGIN
 target:=curation_observe_club(payload);
 SELECT * INTO result FROM curation_club_policy(payload);
 IF result.disposition='blocked' OR result.entity_id IS NULL OR result.entity_id<>target THEN RAISE EXCEPTION 'Venue is blocked or ambiguous; resolve curation first' USING ERRCODE='23514'; END IF;
 IF curation_club_keys(payload)='[]'::jsonb THEN RAISE EXCEPTION 'Venue approval requires a stable ID or name and address' USING ERRCODE='23514'; END IF;
 INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
 SELECT gen_random_uuid()::text,id,version+1,'approve',disposition,'approved',actor,reason FROM curation_entities WHERE id=target AND disposition='pending';
 RETURN target;
END $$;
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON clubs FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON club_aliases FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE OR DELETE ON venue_deny_list FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE ON scraping_sources FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE TRIGGER aa_intake_lock BEFORE INSERT OR UPDATE ON shows FOR EACH STATEMENT EXECUTE FUNCTION curation_serialize_intake();
CREATE FUNCTION curation_guard_club_write() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE result record; payload jsonb;
BEGIN
 payload:=to_jsonb(NEW);
 IF TG_OP='INSERT' THEN payload:=payload-'id'; END IF;
 -- Suppression is always allowed, including hiding a routing proxy. It does
 -- not change the curation ledger, source configuration or operating status.
 IF TG_OP='UPDATE' AND NOT NEW.visible AND (to_jsonb(NEW)-'visible') IS NOT DISTINCT FROM (to_jsonb(OLD)-'visible') THEN RETURN NEW; END IF;
 SELECT * INTO result FROM curation_club_policy(payload||jsonb_build_object('id',NEW.id));
 IF result.disposition<>'approved' THEN
  PERFORM curation_observe_club(payload);
  IF TG_OP='UPDATE' THEN RETURN OLD; ELSE RETURN NULL; END IF;
 END IF;
 -- Let an exact existing name reach ON CONFLICT and the UPDATE guard.
 -- A different name must not create a second public row for this identity.
 IF TG_OP='INSERT' AND result.club_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM clubs WHERE id=result.club_id AND name=NEW.name) THEN RETURN NULL; END IF;
 PERFORM curation_observe_club(payload);
 RETURN NEW;
END $$;
CREATE TRIGGER curation_club_write BEFORE INSERT OR UPDATE ON clubs FOR EACH ROW EXECUTE FUNCTION curation_guard_club_write();
CREATE FUNCTION curation_bind_club() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target text;
BEGIN
 SELECT entity_id INTO target FROM curation_club_policy(to_jsonb(NEW)-'id');
 UPDATE curation_entities SET club_id=NEW.id WHERE id=target AND club_id IS NULL;
 PERFORM curation_observe_club(to_jsonb(NEW));
 RETURN NEW;
END $$;
CREATE TRIGGER curation_club_bind AFTER INSERT ON clubs FOR EACH ROW EXECUTE FUNCTION curation_bind_club();
CREATE FUNCTION curation_guard_club_child() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE club record; result record; payload jsonb; keys jsonb:='[]';
BEGIN
 SELECT * INTO club FROM clubs WHERE id=NEW.club_id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 payload:=to_jsonb(club);
 IF TG_TABLE_NAME='scraping_sources' THEN keys:=curation_club_source_keys(to_jsonb(NEW)); END IF;
 -- Explicit suppression remains available even while policy is pending/blocked.
 IF TG_OP='UPDATE' AND TG_TABLE_NAME='shows' AND (to_jsonb(NEW)->>'visible')='false'
 AND (to_jsonb(NEW)-'visible') IS NOT DISTINCT FROM (to_jsonb(OLD)-'visible') THEN RETURN NEW; END IF;
 IF TG_OP='UPDATE' AND TG_TABLE_NAME='scraping_sources' AND (to_jsonb(NEW)->>'enabled')='false'
 AND (to_jsonb(NEW)-'enabled') IS NOT DISTINCT FROM (to_jsonb(OLD)-'enabled') THEN RETURN NEW; END IF;
 SELECT * INTO result FROM curation_club_policy(payload,keys);
 IF result.disposition<>'approved' OR result.club_id IS DISTINCT FROM NEW.club_id THEN
  PERFORM curation_observe_club(payload,keys,TG_TABLE_NAME);
  IF TG_OP='UPDATE' THEN RETURN OLD; ELSE RETURN NULL; END IF;
 END IF;
 IF TG_TABLE_NAME='scraping_sources' THEN PERFORM curation_observe_club(payload,keys,'scraping_sources'); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_club_show BEFORE INSERT OR UPDATE ON shows FOR EACH ROW EXECUTE FUNCTION curation_guard_club_child();
CREATE TRIGGER curation_club_source BEFORE INSERT OR UPDATE ON scraping_sources FOR EACH ROW EXECUTE FUNCTION curation_guard_club_child();
CREATE FUNCTION curation_capture_club_keys(public_id integer) RETURNS void LANGUAGE plpgsql AS $$
DECLARE payload jsonb; alias record; source record;
BEGIN
 SELECT to_jsonb(c) INTO payload FROM clubs c WHERE c.id=public_id;
 IF payload IS NULL THEN RETURN; END IF;
 PERFORM curation_observe_club(payload);
 FOR source IN SELECT * FROM scraping_sources WHERE club_id=public_id LOOP
  PERFORM curation_observe_club(payload,curation_club_source_keys(to_jsonb(source)),'scraping_sources');
 END LOOP;
 FOR alias IN SELECT * FROM club_aliases WHERE club_id=public_id AND verified LOOP
  PERFORM curation_observe_club(payload||jsonb_build_object('name',alias.alias_name,'city',alias.city,'state',alias.state),'[]','club_aliases');
 END LOOP;
END $$;
-- Projection is driven by the ledger, including direct imports/legacy denials.
CREATE FUNCTION curation_project_club_block() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE public_id integer;
BEGIN
 IF NEW.entity_id IS NOT NULL AND NEW.action='block' THEN
  SELECT club_id INTO public_id FROM curation_entities WHERE id=NEW.entity_id AND kind='club';
  IF public_id IS NOT NULL THEN
   PERFORM curation_capture_club_keys(public_id);
   UPDATE clubs SET visible=false WHERE id=public_id;
   UPDATE shows SET visible=false WHERE club_id=public_id;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER zz_curation_club_block AFTER INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_project_club_block();
CREATE FUNCTION curation_record_venue_denial() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE payload jsonb; target text;
BEGIN
 SELECT to_jsonb(c) INTO payload FROM clubs c WHERE google_place_id=NEW.google_place_id ORDER BY id LIMIT 1;
 payload:=coalesce(payload,'{}'::jsonb)||jsonb_build_object('name',NEW.name,'google_place_id',NEW.google_place_id);
 target:=curation_observe_club(payload,'[]','venue_deny_list');
 RETURN NEW;
END $$;
CREATE TRIGGER curation_venue_denial AFTER INSERT OR UPDATE ON venue_deny_list FOR EACH ROW EXECUTE FUNCTION curation_record_venue_denial();

CREATE FUNCTION curation_retain_club_alias() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE payload jsonb;
BEGIN
 SELECT to_jsonb(c) INTO payload FROM clubs c WHERE c.id=NEW.club_id;
 IF NEW.verified AND payload IS NOT NULL THEN
  PERFORM curation_observe_club(payload||jsonb_build_object('name',NEW.alias_name,'city',NEW.city,'state',NEW.state),'[]','club_aliases');
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_club_alias AFTER INSERT OR UPDATE ON club_aliases FOR EACH ROW EXECUTE FUNCTION curation_retain_club_alias();
CREATE FUNCTION curation_retain_club_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM curation_capture_club_keys(OLD.id);
 RETURN OLD;
END $$;
CREATE TRIGGER curation_club_delete BEFORE DELETE ON clubs FOR EACH ROW EXECUTE FUNCTION curation_retain_club_identity();

-- Retain old compatibility denials even when removed before reconciliation.
CREATE FUNCTION curation_retain_venue_denial() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM curation_observe_club(jsonb_build_object('name',OLD.name,'google_place_id',OLD.google_place_id),'[]','venue_deny_list');
 RETURN OLD;
END $$;
CREATE TRIGGER curation_venue_denial_delete BEFORE DELETE ON venue_deny_list FOR EACH ROW EXECUTE FUNCTION curation_retain_venue_denial();

-- Imported negative decisions predate the projection trigger. Reconcile only
-- their public visibility; do not infer approval or alter source configuration.
DO $$ DECLARE venue record; BEGIN
 FOR venue IN SELECT club_id FROM curation_entities WHERE kind='club' AND disposition='blocked' AND club_id IS NOT NULL LOOP
  PERFORM curation_capture_club_keys(venue.club_id);
 END LOOP;
END $$;
UPDATE clubs SET visible=false WHERE id IN (SELECT club_id FROM curation_entities WHERE kind='club' AND disposition='blocked');
UPDATE shows SET visible=false WHERE club_id IN (SELECT club_id FROM curation_entities WHERE kind='club' AND disposition='blocked');
