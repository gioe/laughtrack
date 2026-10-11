-- UI commands are validated/applied by the existing Python ReviewStore.
CREATE TABLE comedy_admin_review_requests (
  id text PRIMARY KEY,
  candidate_id integer NOT NULL REFERENCES comedy_event_candidates(id) ON DELETE RESTRICT,
  actor text NOT NULL,
  action text NOT NULL CHECK (action IN ('approve','reject','defer')),
  reason text NOT NULL CHECK (length(trim(reason)) BETWEEN 1 AND 2000),
  snapshot jsonb NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','applied','stale')),
  result jsonb,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);
CREATE INDEX comedy_admin_review_requests_candidate_idx ON comedy_admin_review_requests(candidate_id,created_at);
CREATE UNIQUE INDEX comedy_admin_review_requests_pending_idx ON comedy_admin_review_requests(candidate_id) WHERE status='pending';
