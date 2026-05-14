CREATE TABLE podcasts (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    source_podcast_id TEXT NOT NULL,
    feed_url TEXT,
    title TEXT NOT NULL,
    author_name TEXT,
    website_url TEXT,
    image_url TEXT,
    description TEXT,
    external_ids JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_payload JSONB,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX podcasts_source_podcast_id_key
    ON podcasts(source, source_podcast_id);

CREATE INDEX podcasts_source_idx
    ON podcasts(source);

CREATE INDEX podcasts_feed_url_idx
    ON podcasts(feed_url);

CREATE TABLE podcast_episodes (
    id SERIAL PRIMARY KEY,
    podcast_id INTEGER NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    source_episode_id TEXT NOT NULL,
    guid TEXT,
    title TEXT NOT NULL,
    description TEXT,
    release_date TIMESTAMPTZ,
    duration_seconds INTEGER,
    episode_url TEXT,
    audio_url TEXT,
    external_ids JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX podcast_episodes_source_episode_id_key
    ON podcast_episodes(source, source_episode_id);

CREATE INDEX podcast_episodes_podcast_id_idx
    ON podcast_episodes(podcast_id);

CREATE INDEX podcast_episodes_podcast_id_release_date_idx
    ON podcast_episodes(podcast_id, release_date);

CREATE INDEX podcast_episodes_guid_idx
    ON podcast_episodes(guid);

CREATE TABLE comedian_podcasts (
    id SERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
    podcast_id INTEGER NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
    association_type TEXT NOT NULL,
    source TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending',
    confidence DOUBLE PRECISION NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT comedian_podcasts_association_type_check
        CHECK (association_type IN ('host', 'cohost', 'owner', 'producer', 'network', 'other')),
    CONSTRAINT comedian_podcasts_review_status_check
        CHECK (review_status IN ('pending', 'accepted', 'rejected'))
);

CREATE UNIQUE INDEX comedian_podcasts_comedian_podcast_type_source_key
    ON comedian_podcasts(comedian_id, podcast_id, association_type, source);

CREATE INDEX comedian_podcasts_comedian_id_idx
    ON comedian_podcasts(comedian_id);

CREATE INDEX comedian_podcasts_podcast_id_idx
    ON comedian_podcasts(podcast_id);

CREATE INDEX comedian_podcasts_review_status_idx
    ON comedian_podcasts(review_status);

CREATE INDEX comedian_podcasts_source_idx
    ON comedian_podcasts(source);

CREATE TABLE podcast_candidate_reviews (
    id SERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
    podcast_id INTEGER REFERENCES podcasts(id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    source_podcast_id TEXT NOT NULL,
    candidate_status TEXT NOT NULL DEFAULT 'pending',
    association_type TEXT,
    confidence DOUBLE PRECISION NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT podcast_candidate_reviews_candidate_status_check
        CHECK (candidate_status IN ('pending', 'accepted', 'rejected')),
    CONSTRAINT podcast_candidate_reviews_association_type_check
        CHECK (association_type IS NULL OR association_type IN ('host', 'cohost', 'owner', 'producer', 'network', 'other'))
);

CREATE UNIQUE INDEX podcast_candidate_reviews_comedian_source_podcast_key
    ON podcast_candidate_reviews(comedian_id, source, source_podcast_id);

CREATE INDEX podcast_candidate_reviews_comedian_id_idx
    ON podcast_candidate_reviews(comedian_id);

CREATE INDEX podcast_candidate_reviews_podcast_id_idx
    ON podcast_candidate_reviews(podcast_id);

CREATE INDEX podcast_candidate_reviews_candidate_status_idx
    ON podcast_candidate_reviews(candidate_status);

CREATE INDEX podcast_candidate_reviews_source_podcast_id_idx
    ON podcast_candidate_reviews(source, source_podcast_id);

CREATE TABLE episode_appearances (
    id SERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
    episode_id INTEGER NOT NULL REFERENCES podcast_episodes(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    appearance_role TEXT NOT NULL DEFAULT 'guest',
    review_status TEXT NOT NULL DEFAULT 'pending',
    confidence DOUBLE PRECISION NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT episode_appearances_appearance_role_check
        CHECK (appearance_role IN ('guest', 'host', 'mention', 'other')),
    CONSTRAINT episode_appearances_review_status_check
        CHECK (review_status IN ('pending', 'accepted', 'rejected'))
);

CREATE UNIQUE INDEX episode_appearances_comedian_episode_source_key
    ON episode_appearances(comedian_id, episode_id, source);

CREATE INDEX episode_appearances_comedian_id_idx
    ON episode_appearances(comedian_id);

CREATE INDEX episode_appearances_episode_id_idx
    ON episode_appearances(episode_id);

CREATE INDEX episode_appearances_review_status_idx
    ON episode_appearances(review_status);

CREATE INDEX episode_appearances_source_idx
    ON episode_appearances(source);

CREATE TABLE episode_appearance_reviews (
    id SERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
    episode_id INTEGER REFERENCES podcast_episodes(id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    source_episode_id TEXT NOT NULL,
    candidate_status TEXT NOT NULL DEFAULT 'pending',
    appearance_role TEXT NOT NULL DEFAULT 'guest',
    confidence DOUBLE PRECISION NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT episode_appearance_reviews_candidate_status_check
        CHECK (candidate_status IN ('pending', 'accepted', 'rejected')),
    CONSTRAINT episode_appearance_reviews_appearance_role_check
        CHECK (appearance_role IN ('guest', 'host', 'mention', 'other'))
);

CREATE UNIQUE INDEX episode_appearance_reviews_comedian_source_episode_key
    ON episode_appearance_reviews(comedian_id, source, source_episode_id);

CREATE INDEX episode_appearance_reviews_comedian_id_idx
    ON episode_appearance_reviews(comedian_id);

CREATE INDEX episode_appearance_reviews_episode_id_idx
    ON episode_appearance_reviews(episode_id);

CREATE INDEX episode_appearance_reviews_candidate_status_idx
    ON episode_appearance_reviews(candidate_status);

CREATE INDEX episode_appearance_reviews_source_episode_id_idx
    ON episode_appearance_reviews(source, source_episode_id);
