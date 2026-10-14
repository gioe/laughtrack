-- Additive curation substrate. No existing domain rows or enforcement are changed.
CREATE TABLE curation_entities (
 id text PRIMARY KEY,
 kind text NOT NULL CHECK(kind IN ('comedian','club','show','podcast')),
 identity_scope text NOT NULL DEFAULT 'entity' CHECK(identity_scope IN ('entity','name','series')),
 label text NOT NULL CHECK(length(btrim(label))>0),
 disposition text NOT NULL DEFAULT 'pending' CHECK(disposition IN ('pending','approved','blocked')),
 version integer NOT NULL DEFAULT 0 CHECK(version>=0),
 comedian_id integer UNIQUE REFERENCES comedians(id) ON DELETE SET NULL ON UPDATE RESTRICT,
 club_id integer UNIQUE REFERENCES clubs(id) ON DELETE SET NULL ON UPDATE RESTRICT,
 show_id integer UNIQUE REFERENCES shows(id) ON DELETE SET NULL ON UPDATE RESTRICT,
 podcast_id integer UNIQUE REFERENCES podcasts(id) ON DELETE SET NULL ON UPDATE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(id,kind,identity_scope),
 CHECK(identity_scope<>'series' OR kind='show'),
 CHECK(identity_scope='entity' OR disposition<>'approved'),
 CHECK(comedian_id IS NULL OR (kind='comedian' AND identity_scope='entity')),
 CHECK(club_id IS NULL OR (kind='club' AND identity_scope='entity')),
 CHECK(show_id IS NULL OR (kind='show' AND identity_scope='entity')),
 CHECK(podcast_id IS NULL OR (kind='podcast' AND identity_scope='entity'))
);
CREATE INDEX curation_entities_queue ON curation_entities(kind,disposition,created_at,id);
CREATE TABLE curation_identity_keys (
 id text PRIMARY KEY,
 entity_id text NOT NULL,
 entity_kind text NOT NULL,
 identity_scope text NOT NULL,
 key_type text NOT NULL CHECK(key_type IN ('external_id','legacy_id','feed_url','exact_name','series_id')),
 namespace text NOT NULL CHECK(namespace ~ '^[a-z0-9][a-z0-9_.:-]*$'),
 scope text NOT NULL CHECK(length(btrim(scope))>0 AND scope=btrim(scope)),
 value text NOT NULL CHECK(length(btrim(value))>0),
 created_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT curation_identity_keys_entity_fkey FOREIGN KEY(entity_id,entity_kind,identity_scope) REFERENCES curation_entities(id,kind,identity_scope) ON DELETE RESTRICT ON UPDATE RESTRICT,
 UNIQUE(entity_kind,namespace,scope,value),
 CHECK((key_type='exact_name' AND identity_scope='name' AND namespace='exact-name:v1')
    OR (key_type='series_id' AND identity_scope='series' AND entity_kind='show')
    OR (key_type IN ('external_id','legacy_id','feed_url') AND identity_scope='entity'))
);
CREATE INDEX curation_identity_keys_entity ON curation_identity_keys(entity_id);
CREATE TABLE curation_relationships (
 id text PRIMARY KEY,
 kind text NOT NULL CHECK(kind IN ('alias_of','host_of','cohost_of')),
 source_id text NOT NULL,
 source_kind text NOT NULL DEFAULT 'comedian' CHECK(source_kind='comedian'),
 source_scope text NOT NULL DEFAULT 'entity' CHECK(source_scope='entity'),
 target_id text NOT NULL,
 target_kind text NOT NULL,
 target_scope text NOT NULL DEFAULT 'entity' CHECK(target_scope='entity'),
 disposition text NOT NULL DEFAULT 'proposed' CHECK(disposition IN ('proposed','confirmed','rejected','severed')),
 version integer NOT NULL DEFAULT 0 CHECK(version>=0),
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(source_id,source_kind,source_scope) REFERENCES curation_entities(id,kind,identity_scope) ON DELETE RESTRICT ON UPDATE RESTRICT,
 FOREIGN KEY(target_id,target_kind,target_scope) REFERENCES curation_entities(id,kind,identity_scope) ON DELETE RESTRICT ON UPDATE RESTRICT,
 UNIQUE(kind,source_id,target_id),
 CHECK(source_id<>target_id),
 CHECK((kind='alias_of' AND target_kind='comedian') OR (kind IN ('host_of','cohost_of') AND target_kind='podcast'))
);
CREATE UNIQUE INDEX curation_relationships_one_parent ON curation_relationships(source_id) WHERE kind='alias_of' AND disposition='confirmed';
CREATE INDEX curation_relationships_target ON curation_relationships(target_id);
CREATE INDEX curation_relationships_queue ON curation_relationships(kind,disposition,created_at,id);
-- A real write serializes graph changes, including under REPEATABLE READ.
-- An advisory lock alone would not refresh an older transaction snapshot.
CREATE TABLE curation_graph_lock (id integer PRIMARY KEY CHECK(id=1), version bigint NOT NULL DEFAULT 0);
INSERT INTO curation_graph_lock(id) VALUES(1);
CREATE TABLE curation_observations (
 id text PRIMARY KEY,
 entity_id text REFERENCES curation_entities(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 relationship_id text REFERENCES curation_relationships(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 source text NOT NULL CHECK(length(btrim(source))>0),
 source_key text NOT NULL CHECK(length(btrim(source_key))>0),
 fingerprint text NOT NULL CHECK(length(btrim(fingerprint))>0),
 evidence jsonb NOT NULL CHECK(jsonb_typeof(evidence)='object'),
 observed_at timestamptz NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now(),
 CHECK(num_nonnulls(entity_id,relationship_id)=1),
 CONSTRAINT curation_observations_entity_fingerprint_key UNIQUE(entity_id,source,source_key,fingerprint),
 CONSTRAINT curation_observations_relationship_fingerprint_key UNIQUE(relationship_id,source,source_key,fingerprint)
);
CREATE TABLE curation_decisions (
 id text PRIMARY KEY,
 entity_id text REFERENCES curation_entities(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 relationship_id text REFERENCES curation_relationships(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 version integer NOT NULL CHECK(version>0),
 action text NOT NULL CHECK(action IN ('approve','block','restore','confirm','reject','sever')),
 before_state text NOT NULL,
 after_state text NOT NULL,
 actor text NOT NULL CHECK(length(btrim(actor))>0),
 reason text NOT NULL CHECK(length(btrim(reason))>0),
 evidence jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(evidence)='object'),
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(num_nonnulls(entity_id,relationship_id)=1),
 UNIQUE(entity_id,version),
 UNIQUE(relationship_id,version)
);
CREATE TABLE curation_requests (
 id text PRIMARY KEY,
 entity_id text REFERENCES curation_entities(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 relationship_id text REFERENCES curation_relationships(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 expected_version integer NOT NULL CHECK(expected_version>=0),
 action text NOT NULL,
 actor text NOT NULL CHECK(length(btrim(actor))>0),
 reason text NOT NULL CHECK(length(btrim(reason))>0),
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','applied','conflict','failed','canceled')),
 decision_id text UNIQUE REFERENCES curation_decisions(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
 error text,
 created_at timestamptz NOT NULL DEFAULT now(),
 completed_at timestamptz,
 CHECK(num_nonnulls(entity_id,relationship_id)=1),
 CHECK((entity_id IS NOT NULL AND action IN ('approve','block','restore')) OR
       (relationship_id IS NOT NULL AND action IN ('confirm','reject','sever','restore'))),
 CHECK((status='applied')=(decision_id IS NOT NULL)),
 CHECK((status='pending')=(completed_at IS NULL))
);
CREATE INDEX curation_requests_queue ON curation_requests(status,created_at,id);
CREATE INDEX curation_requests_entity ON curation_requests(entity_id,created_at);
CREATE INDEX curation_requests_relationship ON curation_requests(relationship_id,created_at);

CREATE FUNCTION curation_immutable_record() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'Curation evidence, keys and decisions are append-only' USING ERRCODE='23514';
END $$;
CREATE TRIGGER curation_keys_immutable BEFORE UPDATE OR DELETE ON curation_identity_keys FOR EACH ROW EXECUTE FUNCTION curation_immutable_record();
CREATE TRIGGER curation_observations_immutable BEFORE UPDATE OR DELETE ON curation_observations FOR EACH ROW EXECUTE FUNCTION curation_immutable_record();
CREATE TRIGGER curation_decisions_immutable BEFORE UPDATE OR DELETE ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_immutable_record();

CREATE FUNCTION curation_guard_entity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.disposition<>'pending' OR NEW.version<>0 THEN RAISE EXCEPTION 'Create pending curation identities, then record a decision' USING ERRCODE='23514'; END IF;
 ELSE
  IF (NEW.id,NEW.kind,NEW.identity_scope) IS DISTINCT FROM (OLD.id,OLD.kind,OLD.identity_scope) THEN
   RAISE EXCEPTION 'Curation identity and kind are immutable' USING ERRCODE='23514';
  END IF;
  IF (NEW.disposition,NEW.version) IS DISTINCT FROM (OLD.disposition,OLD.version) AND pg_trigger_depth()<2 THEN
   RAISE EXCEPTION 'Change disposition by appending a curation decision' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_entity_guard BEFORE INSERT OR UPDATE ON curation_entities FOR EACH ROW EXECUTE FUNCTION curation_guard_entity();

CREATE FUNCTION curation_guard_relationship() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.disposition<>'proposed' OR NEW.version<>0 THEN RAISE EXCEPTION 'Create proposed relationships, then record a decision' USING ERRCODE='23514'; END IF;
 ELSE
  IF (NEW.id,NEW.kind,NEW.source_id,NEW.source_kind,NEW.source_scope,NEW.target_id,NEW.target_kind,NEW.target_scope) IS DISTINCT FROM
     (OLD.id,OLD.kind,OLD.source_id,OLD.source_kind,OLD.source_scope,OLD.target_id,OLD.target_kind,OLD.target_scope) THEN
   RAISE EXCEPTION 'Relationship identity is immutable' USING ERRCODE='23514';
  END IF;
  IF (NEW.disposition,NEW.version) IS DISTINCT FROM (OLD.disposition,OLD.version) AND pg_trigger_depth()<2 THEN
   RAISE EXCEPTION 'Change disposition by appending a curation decision' USING ERRCODE='23514';
  END IF;
 END IF;
 IF NEW.kind='alias_of' AND NEW.disposition='confirmed' THEN
  UPDATE curation_graph_lock SET version=version+1 WHERE id=1;
  IF NOT FOUND THEN RAISE EXCEPTION 'Curation graph lock is missing'; END IF;
  IF EXISTS(WITH RECURSIVE ancestors(id) AS (
    SELECT NEW.target_id UNION
    SELECT r.target_id FROM curation_relationships r JOIN ancestors a ON r.source_id=a.id
     WHERE r.kind='alias_of' AND r.disposition='confirmed' AND r.id<>NEW.id
   ) SELECT 1 FROM ancestors WHERE id=NEW.source_id) THEN
    RAISE EXCEPTION 'Curation parent relationship would create a cycle' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_relationship_guard BEFORE INSERT OR UPDATE ON curation_relationships FOR EACH ROW EXECUTE FUNCTION curation_guard_relationship();

CREATE FUNCTION curation_apply_decision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE current_state text; current_version integer; next_state text;
BEGIN
 IF num_nonnulls(NEW.entity_id,NEW.relationship_id)<>1 THEN RAISE EXCEPTION 'A decision requires exactly one target' USING ERRCODE='23514'; END IF;
 IF NEW.entity_id IS NOT NULL THEN
  SELECT disposition,version INTO current_state,current_version FROM curation_entities WHERE id=NEW.entity_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Curation entity not found' USING ERRCODE='23503'; END IF;
  next_state := CASE
   WHEN NEW.action='approve' AND current_state='pending' THEN 'approved'
   WHEN NEW.action='block' AND current_state IN ('pending','approved') THEN 'blocked'
   WHEN NEW.action='restore' AND current_state='blocked' THEN 'pending' END;
 ELSE
  SELECT disposition,version INTO current_state,current_version FROM curation_relationships WHERE id=NEW.relationship_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Curation relationship not found' USING ERRCODE='23503'; END IF;
  next_state := CASE
   WHEN NEW.action='confirm' AND current_state='proposed' THEN 'confirmed'
   WHEN NEW.action='reject' AND current_state='proposed' THEN 'rejected'
   WHEN NEW.action='sever' AND current_state='confirmed' THEN 'severed'
   WHEN NEW.action='restore' AND current_state IN ('rejected','severed') THEN 'proposed' END;
 END IF;
 IF NEW.version<>current_version+1 OR NEW.before_state<>current_state THEN
  RAISE EXCEPTION 'Stale curation decision' USING ERRCODE='40001';
 END IF;
 IF next_state IS NULL OR NEW.after_state<>next_state THEN
  RAISE EXCEPTION 'Invalid curation transition; restoration must be explicit' USING ERRCODE='23514';
 END IF;
 IF NEW.entity_id IS NOT NULL THEN
  UPDATE curation_entities SET disposition=next_state,version=NEW.version WHERE id=NEW.entity_id;
 ELSE
  UPDATE curation_relationships SET disposition=next_state,version=NEW.version WHERE id=NEW.relationship_id;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_decision_apply AFTER INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION curation_apply_decision();

CREATE FUNCTION curation_guard_request() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.status<>'pending' THEN RAISE EXCEPTION 'Requests start pending' USING ERRCODE='23514'; END IF;
 ELSE
  IF (NEW.id,NEW.entity_id,NEW.relationship_id,NEW.expected_version,NEW.action,NEW.actor,NEW.reason,NEW.created_at) IS DISTINCT FROM
     (OLD.id,OLD.entity_id,OLD.relationship_id,OLD.expected_version,OLD.action,OLD.actor,OLD.reason,OLD.created_at) THEN
   RAISE EXCEPTION 'Request payload is immutable' USING ERRCODE='23514';
  END IF;
  IF OLD.status<>'pending' THEN RAISE EXCEPTION 'Completed requests are immutable; submit a new request' USING ERRCODE='23514'; END IF;
 END IF;
 IF NEW.status='applied' AND NOT EXISTS (
  SELECT 1 FROM curation_decisions d WHERE d.id=NEW.decision_id
   AND d.entity_id IS NOT DISTINCT FROM NEW.entity_id
   AND d.relationship_id IS NOT DISTINCT FROM NEW.relationship_id
   AND d.version=NEW.expected_version+1 AND d.action=NEW.action
   AND d.actor=NEW.actor AND d.reason=NEW.reason
 ) THEN RAISE EXCEPTION 'Request result does not match its decision' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER curation_request_guard BEFORE INSERT OR UPDATE ON curation_requests FOR EACH ROW EXECUTE FUNCTION curation_guard_request();
CREATE TRIGGER curation_requests_retained BEFORE DELETE ON curation_requests FOR EACH ROW EXECUTE FUNCTION curation_immutable_record();
