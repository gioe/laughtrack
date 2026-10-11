BEGIN;
CREATE TABLE comedy_source_samples (
 source_id INTEGER NOT NULL REFERENCES scraping_sources(id) ON DELETE RESTRICT,
 event_key TEXT NOT NULL CHECK(length(event_key)>0),
 payload_fingerprint TEXT NOT NULL,
 identity_fingerprint TEXT NOT NULL,
 baseline JSONB NOT NULL CHECK(jsonb_typeof(baseline)='object'),
 policy_version INTEGER NOT NULL CHECK(policy_version>0),
 first_seen_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 last_seen_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(source_id,event_key)
);
CREATE INDEX comedy_source_samples_window_idx ON comedy_source_samples(source_id,last_seen_at);
CREATE TABLE comedy_source_reports (
 id SERIAL PRIMARY KEY,
 source_id INTEGER NOT NULL REFERENCES scraping_sources(id) ON DELETE RESTRICT,
 report_digest TEXT NOT NULL,
 evidence_digest TEXT NOT NULL,
 config JSONB NOT NULL CHECK(jsonb_typeof(config)='object'),
 metrics JSONB NOT NULL CHECK(jsonb_typeof(metrics)='object'),
 recommendation JSONB NOT NULL CHECK(jsonb_typeof(recommendation)='object'),
 source_snapshot JSONB NOT NULL CHECK(jsonb_typeof(source_snapshot)='object'),
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(source_id,report_digest)
);
CREATE TABLE comedy_source_transitions (
 id SERIAL PRIMARY KEY,
 source_id INTEGER NOT NULL REFERENCES scraping_sources(id) ON DELETE RESTRICT,
 report_id INTEGER NOT NULL REFERENCES comedy_source_reports(id) ON DELETE RESTRICT,
 kind TEXT NOT NULL CHECK(kind IN ('downgrade','rollback')),
 rollback_of INTEGER UNIQUE REFERENCES comedy_source_transitions(id) ON DELETE RESTRICT,
 actor TEXT NOT NULL CHECK(length(btrim(actor))>0),
 reason TEXT NOT NULL CHECK(length(btrim(reason))>0),
 before_state JSONB NOT NULL CHECK(jsonb_typeof(before_state)='object'),
 after_state JSONB NOT NULL CHECK(jsonb_typeof(after_state)='object'),
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 CHECK((kind='rollback')=(rollback_of IS NOT NULL))
);
CREATE UNIQUE INDEX comedy_source_one_downgrade_idx ON comedy_source_transitions(report_id) WHERE kind='downgrade';
CREATE INDEX comedy_source_transitions_history_idx ON comedy_source_transitions(source_id,id);
CREATE FUNCTION prevent_comedy_monitor_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Comedy monitor history is append-only'; END;
$$;
CREATE TRIGGER comedy_source_reports_immutable BEFORE UPDATE OR DELETE ON comedy_source_reports
 FOR EACH ROW EXECUTE FUNCTION prevent_comedy_monitor_history_mutation();
CREATE TRIGGER comedy_source_transitions_immutable BEFORE UPDATE OR DELETE ON comedy_source_transitions
 FOR EACH ROW EXECUTE FUNCTION prevent_comedy_monitor_history_mutation();
COMMIT;
