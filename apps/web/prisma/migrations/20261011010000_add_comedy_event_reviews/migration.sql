BEGIN;
ALTER TABLE comedy_event_candidates ADD COLUMN review_version INTEGER NOT NULL DEFAULT 0 CHECK(review_version>=0);
CREATE TABLE comedy_event_observations (
 candidate_id INTEGER NOT NULL REFERENCES comedy_event_candidates(id) ON DELETE RESTRICT,
 generation BIGINT NOT NULL CHECK(generation>0),
 decision_id INTEGER NOT NULL,
 baseline_identity_fingerprint TEXT NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(candidate_id,generation),
 UNIQUE(candidate_id,generation,decision_id),
 FOREIGN KEY(candidate_id,decision_id) REFERENCES comedy_event_decisions(candidate_id,id) ON DELETE RESTRICT
);
-- Historical generations cannot be reliably reconstructed from reused decision revisions.
CREATE TABLE comedy_review_previews (
 id TEXT PRIMARY KEY,
 actor TEXT NOT NULL CHECK(length(btrim(actor))>0),
 action TEXT NOT NULL CHECK(action IN ('approve','reject','defer')),
 reason TEXT NOT NULL CHECK(length(btrim(reason))>0),
 items JSONB NOT NULL CHECK(jsonb_typeof(items)='array' AND jsonb_array_length(items)>0),
 token_digest TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 expires_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE comedy_review_operations (
 idempotency_key TEXT PRIMARY KEY,
 preview_id TEXT NOT NULL UNIQUE REFERENCES comedy_review_previews(id) ON DELETE RESTRICT,
 actor TEXT NOT NULL,
 token_digest TEXT NOT NULL,
 result JSONB NOT NULL CHECK(jsonb_typeof(result)='object'),
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE comedy_event_reviews (
 id SERIAL PRIMARY KEY,
 candidate_id INTEGER NOT NULL REFERENCES comedy_event_candidates(id) ON DELETE RESTRICT,
 observation_generation BIGINT NOT NULL,
 decision_id INTEGER NOT NULL,
 review_version INTEGER NOT NULL CHECK(review_version>0),
 payload_fingerprint TEXT NOT NULL,
 identity_fingerprint TEXT NOT NULL,
 policy_version INTEGER NOT NULL CHECK(policy_version>0),
 actor TEXT NOT NULL CHECK(length(btrim(actor))>0),
 reason TEXT NOT NULL CHECK(length(btrim(reason))>0),
 action TEXT NOT NULL CHECK(action IN ('approve','reject','defer')),
 operation_key TEXT NOT NULL REFERENCES comedy_review_operations(idempotency_key) ON DELETE RESTRICT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(candidate_id,review_version),
 FOREIGN KEY(candidate_id,observation_generation,decision_id) REFERENCES comedy_event_observations(candidate_id,generation,decision_id) ON DELETE RESTRICT,
 FOREIGN KEY(candidate_id,decision_id) REFERENCES comedy_event_decisions(candidate_id,id) ON DELETE RESTRICT
);
CREATE INDEX comedy_event_reviews_operation_idx ON comedy_event_reviews(operation_key);
CREATE FUNCTION prevent_comedy_review_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Comedy review history is append-only'; END;
$$;
CREATE TRIGGER comedy_observations_immutable BEFORE UPDATE OR DELETE ON comedy_event_observations
 FOR EACH ROW EXECUTE FUNCTION prevent_comedy_review_history_mutation();
CREATE TRIGGER comedy_reviews_immutable BEFORE UPDATE OR DELETE ON comedy_event_reviews
 FOR EACH ROW EXECUTE FUNCTION prevent_comedy_review_history_mutation();
CREATE TRIGGER comedy_previews_immutable BEFORE UPDATE OR DELETE ON comedy_review_previews
 FOR EACH ROW EXECUTE FUNCTION prevent_comedy_review_history_mutation();
CREATE TRIGGER comedy_operations_immutable BEFORE UPDATE OR DELETE ON comedy_review_operations
 FOR EACH ROW EXECUTE FUNCTION prevent_comedy_review_history_mutation();
COMMIT;
