CREATE UNIQUE INDEX podcast_episodes_unique_podcast_release_title
    ON podcast_episodes (
        podcast_id,
        release_date,
        LOWER(REGEXP_REPLACE(BTRIM(title), '^\s*(?:(?:ep(?:isode)?|#)\s*[0-9]+(?:\s*[:.\-\)\]]|\s+)\s*|[0-9]+\s*[:.\-\)\]]\s*)', '', 'i'))
    )
    WHERE release_date IS NOT NULL
      AND created_at >= TIMESTAMPTZ '2026-06-08 16:00:00+00';
