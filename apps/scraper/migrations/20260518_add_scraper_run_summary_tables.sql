-- TASK-2270: Persist scraper run summaries for admin portal queries.
-- Keeps the existing JSON metrics files while adding normalized Postgres rows.

CREATE TABLE IF NOT EXISTS scraper_runs (
    id BIGSERIAL PRIMARY KEY,
    run_key TEXT NOT NULL UNIQUE,
    exported_at TIMESTAMPTZ NOT NULL,
    duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
    shows_scraped INTEGER NOT NULL DEFAULT 0,
    shows_saved INTEGER NOT NULL DEFAULT 0,
    shows_inserted INTEGER NOT NULL DEFAULT 0,
    shows_updated INTEGER NOT NULL DEFAULT 0,
    shows_failed_save INTEGER NOT NULL DEFAULT 0,
    shows_skipped_dedup INTEGER NOT NULL DEFAULT 0,
    shows_validation_failed INTEGER NOT NULL DEFAULT 0,
    shows_db_errors INTEGER NOT NULL DEFAULT 0,
    clubs_processed INTEGER NOT NULL DEFAULT 0,
    clubs_successful INTEGER NOT NULL DEFAULT 0,
    clubs_failed INTEGER NOT NULL DEFAULT 0,
    errors_total INTEGER NOT NULL DEFAULT 0,
    success_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
    raw_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scraper_run_clubs (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES scraper_runs(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    club_name TEXT NOT NULL,
    club_id INTEGER NULL REFERENCES clubs(id) ON DELETE SET NULL,
    num_shows INTEGER NOT NULL DEFAULT 0,
    execution_time_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT NULL,
    shows_inserted INTEGER NULL,
    shows_updated INTEGER NULL,
    shows_saved INTEGER NULL,
    shows_failed_save INTEGER NULL,
    errors_count INTEGER NULL,
    success_rate DOUBLE PRECISION NULL,
    shows_skipped_dedup INTEGER NULL,
    shows_validation_failed INTEGER NULL,
    shows_db_errors INTEGER NULL,
    http_status INTEGER NULL,
    bot_block_detected BOOLEAN NOT NULL DEFAULT FALSE,
    bot_block_signature TEXT NULL,
    bot_block_provider TEXT NULL,
    bot_block_type TEXT NULL,
    bot_block_source TEXT NULL,
    bot_block_stage TEXT NULL,
    playwright_fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
    items_before_filter INTEGER NULL,
    raw_stat JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, ordinal)
);

CREATE TABLE IF NOT EXISTS scraper_run_errors (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES scraper_runs(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    club_name TEXT NOT NULL,
    error_message TEXT NULL,
    execution_time_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
    raw_error JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_scraper_runs_exported_at
    ON scraper_runs (exported_at DESC);

CREATE INDEX IF NOT EXISTS idx_scraper_run_clubs_run_id
    ON scraper_run_clubs (run_id);

CREATE INDEX IF NOT EXISTS idx_scraper_run_clubs_club_id
    ON scraper_run_clubs (club_id);

CREATE INDEX IF NOT EXISTS idx_scraper_run_errors_run_id
    ON scraper_run_errors (run_id);
