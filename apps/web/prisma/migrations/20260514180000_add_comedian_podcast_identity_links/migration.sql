CREATE TABLE comedian_podcast_identity_links (
    id SERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    source_feed_id TEXT NOT NULL,
    source_feed_url TEXT,
    source_feed_name TEXT,
    review_status TEXT NOT NULL,
    review_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT comedian_podcast_identity_links_review_status_check
        CHECK (review_status IN ('verified', 'ambiguous', 'rejected'))
);

CREATE UNIQUE INDEX comedian_podcast_identity_links_comedian_source_feed_key
    ON comedian_podcast_identity_links(comedian_id, source, source_feed_id);

CREATE INDEX comedian_podcast_identity_links_comedian_id_idx
    ON comedian_podcast_identity_links(comedian_id);

CREATE INDEX comedian_podcast_identity_links_source_feed_id_idx
    ON comedian_podcast_identity_links(source, source_feed_id);

CREATE INDEX comedian_podcast_identity_links_review_status_idx
    ON comedian_podcast_identity_links(review_status);
