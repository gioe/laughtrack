-- [TASK-2041] Add generic chain-level scraper defaults.
-- Per-club scraping_sources remain the source of source_url, typed venue ids,
-- priority, and enabled state. Chain defaults only provide shared scraper
-- intent for a chain when a club source leaves scraper_key blank.

CREATE TABLE IF NOT EXISTS chain_scraping_defaults (
    id SERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL REFERENCES chains(id) ON DELETE CASCADE,
    platform "ScrapingPlatform" NOT NULL,
    scraper_key TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS chain_scraping_defaults_chain_platform_priority_key
    ON chain_scraping_defaults (chain_id, platform, priority);

CREATE INDEX IF NOT EXISTS chain_scraping_defaults_chain_enabled_priority_idx
    ON chain_scraping_defaults (chain_id, enabled, priority);

CREATE INDEX IF NOT EXISTS chain_scraping_defaults_platform_enabled_idx
    ON chain_scraping_defaults (platform, enabled);

CREATE OR REPLACE FUNCTION set_chain_scraping_defaults_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chain_scraping_defaults_set_updated_at ON chain_scraping_defaults;

CREATE TRIGGER chain_scraping_defaults_set_updated_at
BEFORE UPDATE ON chain_scraping_defaults
FOR EACH ROW
EXECUTE FUNCTION set_chain_scraping_defaults_updated_at();
