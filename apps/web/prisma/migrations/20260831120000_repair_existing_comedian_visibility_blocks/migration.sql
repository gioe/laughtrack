-- Existing comedian rows are suppressed by comedians.visible. The deny list is
-- reserved for names that have not been ingested, so repair every overlap that
-- admin block actions created after the original visibility consolidation.

ALTER TABLE comedians ADD COLUMN block_reason TEXT;
ALTER TABLE comedians ADD COLUMN block_added_by TEXT;
ALTER TABLE comedians ADD COLUMN block_added_at TIMESTAMPTZ;

-- Preserve every source row, including multiple spellings that normalize to
-- one comedian. This table is deliberately independent of both source tables
-- so the evidence survives an unblock, rename, or comedian deletion.
CREATE TABLE comedian_visibility_block_archive (
    id BIGSERIAL PRIMARY KEY,
    comedian_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    reason TEXT NOT NULL,
    added_by TEXT NOT NULL,
    deleted_at TIMESTAMPTZ NOT NULL,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX comedian_visibility_block_archive_comedian_id_idx
    ON comedian_visibility_block_archive (comedian_id, archived_at DESC);

WITH matched AS (
    SELECT c.id AS comedian_id,
           d.name,
           d.reason,
           d.added_by,
           d.deleted_at,
           row_number() OVER (
               PARTITION BY c.id
               ORDER BY d.deleted_at DESC, d.name ASC
           ) AS recency_rank
    FROM comedian_deny_list d
    JOIN comedians c
      ON lower(btrim(regexp_replace(replace(c.name, chr(160), ' '),
                                    '[[:space:]]+', ' ', 'g')))
       = lower(btrim(regexp_replace(replace(d.name, chr(160), ' '),
                                    '[[:space:]]+', ' ', 'g')))
),
archived AS (
    INSERT INTO comedian_visibility_block_archive (
        comedian_id,
        name,
        reason,
        added_by,
        deleted_at
    )
    SELECT comedian_id, name, reason, added_by, deleted_at
    FROM matched
    RETURNING comedian_id
),
promoted AS (
    UPDATE comedians c
       SET visible = false,
           block_reason = m.reason,
           block_added_by = m.added_by,
           block_added_at = m.deleted_at
      FROM matched m
     WHERE m.recency_rank = 1
       AND c.id = m.comedian_id
    RETURNING c.id
)
DELETE FROM comedian_deny_list d
WHERE d.name IN (SELECT name FROM matched);
