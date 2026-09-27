-- TASK-4057: RSS durations over 24 hours are untrusted metadata, not
-- evidence that an episode should be deleted. Preserve raw source_payload.
-- Scope to RSS-derived values; other provenance needs its own review.
-- The archive intentionally has no FK so later episode deletion cannot erase
-- the repair audit. No runtime code depends on this migration-owned table.
BEGIN;

CREATE TABLE IF NOT EXISTS podcast_duration_repairs_4057 (
    episode_id integer PRIMARY KEY,
    podcast_id integer NOT NULL,
    source text NOT NULL,
    source_episode_id text NOT NULL,
    original_duration_seconds integer NOT NULL,
    original_updated_at timestamptz NOT NULL,
    repaired_at timestamptz NOT NULL
);

WITH candidates AS MATERIALIZED (
    SELECT id, podcast_id, source, source_episode_id, duration_seconds, updated_at
    FROM podcast_episodes
    WHERE duration_seconds > 86400
      AND source_payload ? 'itunes_duration'
    FOR UPDATE
), archived AS (
    INSERT INTO podcast_duration_repairs_4057 (
        episode_id, podcast_id, source, source_episode_id,
        original_duration_seconds, original_updated_at, repaired_at
    )
    SELECT id, podcast_id, source, source_episode_id,
           duration_seconds, updated_at, CURRENT_TIMESTAMP
    FROM candidates
    ON CONFLICT (episode_id) DO NOTHING
    RETURNING episode_id
)
UPDATE podcast_episodes e
SET duration_seconds = NULL, updated_at = CURRENT_TIMESTAMP
FROM candidates c
WHERE e.id = c.id
  AND EXISTS (SELECT 1 FROM archived a WHERE a.episode_id = c.id);

COMMIT;

-- Guarded rollback (explicit operator action, not executed by this migration):
-- BEGIN;
-- UPDATE podcast_episodes e
-- SET duration_seconds = a.original_duration_seconds,
--     updated_at = a.original_updated_at
-- FROM podcast_duration_repairs_4057 a
-- WHERE e.id = a.episode_id AND e.podcast_id = a.podcast_id
--   AND e.source = a.source AND e.source_episode_id = a.source_episode_id
--   AND e.duration_seconds IS NULL AND e.updated_at = a.repaired_at;
-- COMMIT;
-- Keep the archive after rollback. Reapplying this migration intentionally
-- does not overwrite archived repairs or restore values after a later sync.
