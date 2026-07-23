-- Existing favorites predate this measurement boundary, so their creation time
-- is intentionally unknown. Add the nullable column first, then set the default
-- separately so only future rows are timestamped.
ALTER TABLE favorite_comedians
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

ALTER TABLE favorite_comedians
  ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS favorite_comedians_created_at_comedian_id_idx
  ON favorite_comedians (created_at, comedian_id);
