-- Deploy with scraper workers stopped: older slot-only upserts cannot infer the partial index.
-- Native identities are backfilled by a reviewed repair, never inferred from titles or rooms here.
BEGIN;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS source_performance_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS shows_club_source_performance_key
    ON shows (club_id, source_performance_id) WHERE source_performance_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS shows_legacy_club_date_room_key
    ON shows (club_id, date, room) WHERE source_performance_id IS NULL;
CREATE INDEX IF NOT EXISTS shows_club_id_date_idx ON shows (club_id, date);
DROP INDEX IF EXISTS shows_club_id_date_room_key;
ALTER TABLE shows ADD CONSTRAINT shows_source_performance_nonempty
    CHECK (source_performance_id IS NULL OR length(trim(source_performance_id)) > 0);
COMMIT;
