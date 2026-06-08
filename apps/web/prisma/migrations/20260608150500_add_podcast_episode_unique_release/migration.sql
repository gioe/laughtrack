CREATE UNIQUE INDEX podcast_episodes_unique_podcast_release
    ON podcast_episodes (podcast_id, release_date)
    WHERE release_date IS NOT NULL;
