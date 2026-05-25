CREATE TABLE comedian_podcast_discovery_attempts (
    id SERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    candidates_found INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    searched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT comedian_podcast_discovery_attempts_comedian_source_key UNIQUE (comedian_id, source)
);

CREATE INDEX comedian_podcast_discovery_attempts_source_status_idx
    ON comedian_podcast_discovery_attempts(source, status);

CREATE INDEX comedian_podcast_discovery_attempts_searched_at_idx
    ON comedian_podcast_discovery_attempts(searched_at);
