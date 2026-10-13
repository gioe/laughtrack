-- Identity validation is explicit; existing records are not grandfathered.
ALTER TABLE comedians ADD COLUMN IF NOT EXISTS identity_validated_at timestamptz;
ALTER TABLE comedians ADD COLUMN IF NOT EXISTS identity_validated_by text;
CREATE TABLE IF NOT EXISTS comedian_identity_candidates (
 uuid text PRIMARY KEY, name text NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected')),
 version integer NOT NULL DEFAULT 0,
 canonical_comedian_id integer REFERENCES comedians(id) ON DELETE SET NULL,
 reviewed_by text, reviewed_at timestamptz, reason text,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS comedian_identity_candidates_queue ON comedian_identity_candidates(status,created_at,uuid);
CREATE TABLE IF NOT EXISTS comedian_identity_evidence (
 fingerprint text PRIMARY KEY,
 candidate_uuid text NOT NULL REFERENCES comedian_identity_candidates(uuid) ON DELETE CASCADE,
 show_id integer REFERENCES shows(id) ON DELETE SET NULL,
 source_url text NOT NULL, source_key text NOT NULL,
 extraction_kind text NOT NULL, raw_name text NOT NULL, context text NOT NULL,
 first_seen_at timestamptz NOT NULL DEFAULT now(), last_seen_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS comedian_identity_evidence_candidate ON comedian_identity_evidence(candidate_uuid);
CREATE TABLE IF NOT EXISTS admin_review_decisions (
 id text PRIMARY KEY, workflow text NOT NULL, item_id text NOT NULL,
 actor text NOT NULL, action text NOT NULL, reason text NOT NULL,
 before_json jsonb NOT NULL, after_json jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), undone_at timestamptz
);
CREATE INDEX IF NOT EXISTS admin_review_decisions_item ON admin_review_decisions(workflow,item_id,created_at);
