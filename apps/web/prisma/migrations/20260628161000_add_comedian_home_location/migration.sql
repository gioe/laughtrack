ALTER TABLE comedians
    ADD COLUMN IF NOT EXISTS home_city text,
    ADD COLUMN IF NOT EXISTS home_state text,
    ADD COLUMN IF NOT EXISTS home_country text,
    ADD COLUMN IF NOT EXISTS home_club_id integer,
    ADD COLUMN IF NOT EXISTS home_location_updated_at timestamptz;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'comedians_home_club_id_fkey'
    ) THEN
        ALTER TABLE comedians
            ADD CONSTRAINT comedians_home_club_id_fkey
            FOREIGN KEY (home_club_id)
            REFERENCES clubs(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS comedians_home_club_id_idx
    ON comedians(home_club_id);
