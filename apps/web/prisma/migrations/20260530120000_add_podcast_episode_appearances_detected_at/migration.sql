-- TASK-2527: Bound and rotate the podcast appearance detector so it stops
-- timing out on Neon's statement_timeout.
--
-- detect_podcast_episode_appearances previously loaded every episode for
-- podcasts with accepted comedian associations in one unbounded query. As
-- podcast_episodes grows that query exceeds the statement timeout and the
-- nightly Podcast Episode Sync workflow false-alarms on QueryCanceled.
--
-- appearances_detected_at is a per-episode scan cursor (NULL = never scanned).
-- The detector now orders least-recently-scanned first (NULLS FIRST), takes a
-- bounded --episode-limit batch, and bumps this column for the whole scanned
-- batch — so a bounded run rotates through the full backlog across repeated
-- runs, mirroring sync_podcast_episodes_from_rss's last_synced_at rotation.
-- Existing rows stay NULL so the backlog drains oldest/never-scanned first.

ALTER TABLE podcast_episodes
    ADD COLUMN IF NOT EXISTS appearances_detected_at TIMESTAMPTZ;

-- Composite index aligned with the detector's ORDER BY
-- (appearances_detected_at ASC NULLS FIRST, release_date DESC NULLS LAST, id DESC)
-- so the bounded batch can be served without sorting the full candidate set.
CREATE INDEX IF NOT EXISTS podcast_episodes_appearances_detected_at_idx
    ON podcast_episodes (
        appearances_detected_at ASC NULLS FIRST,
        release_date DESC NULLS LAST,
        id DESC
    );
