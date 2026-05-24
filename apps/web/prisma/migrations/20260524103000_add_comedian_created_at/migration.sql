ALTER TABLE comedians
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS comedians_created_at_idx
ON comedians(created_at DESC, id DESC);
