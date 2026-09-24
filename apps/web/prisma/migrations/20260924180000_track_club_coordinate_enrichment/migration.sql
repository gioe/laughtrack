-- Durable miss/error caching and fair rotation for bounded coordinate enrichment.
ALTER TABLE clubs
    ADD COLUMN IF NOT EXISTS geocode_attempted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS geocode_attempt_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS geocode_outcome TEXT;

CREATE INDEX IF NOT EXISTS clubs_missing_coordinates_geocode_attempt_idx
    ON clubs (geocode_attempted_at ASC NULLS FIRST, id)
    WHERE visible = TRUE AND status = 'active'
      AND club_type IN ('club', 'venue')
      AND (latitude IS NULL OR longitude IS NULL);
