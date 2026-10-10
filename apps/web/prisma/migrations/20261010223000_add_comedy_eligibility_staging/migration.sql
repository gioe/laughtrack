BEGIN;
CREATE TABLE comedy_event_candidates (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES scraping_sources(id) ON DELETE RESTRICT,
    event_key TEXT NOT NULL CHECK (length(event_key) > 0),
    club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE RESTRICT,
    observation_generation BIGINT NOT NULL DEFAULT 1 CHECK (observation_generation > 0),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, event_key)
);
CREATE TABLE comedy_event_decisions (
    id SERIAL PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES comedy_event_candidates(id) ON DELETE RESTRICT,
    payload_fingerprint TEXT NOT NULL,
    identity_fingerprint TEXT NOT NULL,
    policy_version INTEGER NOT NULL CHECK (policy_version > 0),
    classifier_version TEXT NOT NULL CHECK (length(classifier_version) > 0),
    gate_mode TEXT NOT NULL CHECK (gate_mode IN ('shadow', 'enforce')),
    decision TEXT NOT NULL CHECK (decision IN ('accept', 'reject', 'review')),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    evidence JSONB NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT comedy_event_decisions_revision_key UNIQUE (candidate_id, payload_fingerprint, identity_fingerprint, policy_version, classifier_version),
    UNIQUE (candidate_id, id)
);
CREATE TABLE comedy_event_publications (
    candidate_id INTEGER NOT NULL REFERENCES comedy_event_candidates(id) ON DELETE RESTRICT,
    decision_id INTEGER NOT NULL,
    show_id INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (candidate_id, decision_id, show_id),
    FOREIGN KEY (candidate_id, decision_id) REFERENCES comedy_event_decisions(candidate_id, id) ON DELETE RESTRICT
);
CREATE INDEX comedy_event_candidates_club_idx ON comedy_event_candidates(club_id);
CREATE INDEX comedy_event_decisions_review_idx ON comedy_event_decisions(decision, created_at);
CREATE INDEX comedy_event_publications_show_idx ON comedy_event_publications(show_id);
COMMENT ON TABLE comedy_event_decisions IS 'Immutable application decision evidence; retained until an explicit reviewed retention policy is introduced.';
COMMIT;
