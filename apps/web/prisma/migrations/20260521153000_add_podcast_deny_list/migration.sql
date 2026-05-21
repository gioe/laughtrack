CREATE TABLE podcast_deny_list (
    id SERIAL PRIMARY KEY,
    podcast_id INTEGER NULL REFERENCES podcasts(id) ON DELETE SET NULL,
    source TEXT NULL,
    source_podcast_id TEXT NULL,
    feed_url TEXT NULL,
    reason TEXT NULL,
    denied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    denied_by TEXT NULL,
    restored_at TIMESTAMPTZ NULL,
    restored_by TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX podcast_deny_list_podcast_id_key
    ON podcast_deny_list(podcast_id);

CREATE UNIQUE INDEX podcast_deny_list_source_source_podcast_id_key
    ON podcast_deny_list(source, source_podcast_id);

CREATE UNIQUE INDEX podcast_deny_list_feed_url_key
    ON podcast_deny_list(feed_url);

CREATE INDEX podcast_deny_list_restored_at_idx
    ON podcast_deny_list(restored_at);
