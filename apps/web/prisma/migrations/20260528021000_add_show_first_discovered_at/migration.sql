-- Persist the first time a show was discovered by the scraper.
--
-- Existing rows intentionally remain NULL so historical backlog cannot become
-- notification-eligible merely because this migration was deployed. The default
-- applies only to future inserts.
ALTER TABLE shows ADD COLUMN first_discovered_at TIMESTAMPTZ(6);
ALTER TABLE shows ALTER COLUMN first_discovered_at SET DEFAULT NOW();

CREATE INDEX shows_first_discovered_at_idx ON shows (first_discovered_at);
