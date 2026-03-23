-- TASK-589: Add status field to clubs to track closed/inactive venues
-- Adds status enum (active, closed, hiatus) with default 'active' and
-- a nullable closed_at timestamp. All existing clubs inherit 'active'.

ALTER TABLE clubs
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'closed', 'hiatus'));

ALTER TABLE clubs
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ NULL;
