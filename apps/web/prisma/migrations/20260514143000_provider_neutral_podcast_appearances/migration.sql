DROP INDEX IF EXISTS comedian_podcast_appearances_comedian_episode_key;
DROP INDEX IF EXISTS comedian_podcast_appearances_podchaser_episode_id_idx;

ALTER TABLE comedian_podcast_appearances
    RENAME COLUMN podchaser_episode_id TO source_episode_id;

ALTER TABLE comedian_podcast_appearances
    ADD COLUMN source TEXT NOT NULL DEFAULT 'podchaser',
    ADD COLUMN match_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN match_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN match_reviewed_at TIMESTAMPTZ,
    ADD COLUMN match_reviewed_by TEXT;

ALTER TABLE comedian_podcast_appearances
    ALTER COLUMN source DROP DEFAULT,
    ALTER COLUMN match_confidence DROP DEFAULT,
    ALTER COLUMN match_evidence DROP DEFAULT;

CREATE UNIQUE INDEX comedian_podcast_appearances_comedian_source_episode_key
    ON comedian_podcast_appearances(comedian_id, source, source_episode_id);

CREATE INDEX comedian_podcast_appearances_source_episode_id_idx
    ON comedian_podcast_appearances(source, source_episode_id);
