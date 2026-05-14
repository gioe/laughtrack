CREATE TABLE comedian_podcast_appearances (
    id SERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
    podchaser_episode_id TEXT NOT NULL,
    podcast_name TEXT NOT NULL,
    episode_title TEXT NOT NULL,
    release_date TIMESTAMPTZ,
    episode_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX comedian_podcast_appearances_comedian_episode_key
    ON comedian_podcast_appearances(comedian_id, podchaser_episode_id);

CREATE INDEX comedian_podcast_appearances_comedian_id_idx
    ON comedian_podcast_appearances(comedian_id);

CREATE INDEX comedian_podcast_appearances_podchaser_episode_id_idx
    ON comedian_podcast_appearances(podchaser_episode_id);
