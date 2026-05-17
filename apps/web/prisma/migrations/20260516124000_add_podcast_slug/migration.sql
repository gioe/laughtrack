ALTER TABLE podcasts ADD COLUMN slug TEXT;

WITH normalized AS (
    SELECT
        id,
        LOWER(
            REGEXP_REPLACE(
                REGEXP_REPLACE(CONCAT_WS('-', title, source, source_podcast_id), '[^[:alnum:]]+', '-', 'g'),
                '(^-+|-+$)',
                '',
                'g'
            )
        ) AS base_slug
    FROM podcasts
),
ranked AS (
    SELECT
        id,
        COALESCE(NULLIF(base_slug, ''), 'podcast') AS base_slug,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(NULLIF(base_slug, ''), 'podcast')
            ORDER BY id
        ) AS slug_rank
    FROM normalized
)
UPDATE podcasts p
SET slug = CASE
    WHEN ranked.slug_rank = 1 THEN ranked.base_slug
    ELSE ranked.base_slug || '-' || ranked.slug_rank::text
END
FROM ranked
WHERE p.id = ranked.id;

ALTER TABLE podcasts ALTER COLUMN slug SET NOT NULL;

CREATE UNIQUE INDEX podcasts_slug_key
    ON podcasts(slug);
