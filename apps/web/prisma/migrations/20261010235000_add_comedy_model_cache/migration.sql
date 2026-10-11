BEGIN;
CREATE TABLE comedy_model_budget_mutex (id INTEGER PRIMARY KEY CHECK(id=1));
INSERT INTO comedy_model_budget_mutex VALUES (1);
CREATE TABLE comedy_model_attempts (
 token TEXT PRIMARY KEY,
 cache_key TEXT NOT NULL CHECK(length(cache_key)>0),
 budget_day DATE NOT NULL DEFAULT (clock_timestamp() AT TIME ZONE 'UTC')::date,
 reserved_micros BIGINT NOT NULL CHECK(reserved_micros>0),
 charged_micros BIGINT NOT NULL CHECK(charged_micros>=0),
 actual_micros BIGINT CHECK(actual_micros>=0),
 state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','complete','failed')),
 lease_until TIMESTAMPTZ NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 finished_at TIMESTAMPTZ
);
CREATE INDEX comedy_model_attempts_day_idx ON comedy_model_attempts(budget_day);
CREATE INDEX comedy_model_attempts_active_idx ON comedy_model_attempts(state,lease_until);
CREATE INDEX comedy_model_attempts_key_idx ON comedy_model_attempts(cache_key);
CREATE TABLE comedy_model_cache (
 cache_key TEXT PRIMARY KEY,
 owner_token TEXT NOT NULL UNIQUE REFERENCES comedy_model_attempts(token) ON DELETE RESTRICT,
 result JSONB NOT NULL CHECK(jsonb_typeof(result)='object'),
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
COMMIT;
