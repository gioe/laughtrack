-- TASK-4146: upstream JSON-LD shortens some headliners to two words.
-- Use existing canonical identities; do not create abbreviated or accent aliases.
UPDATE scraping_sources
SET metadata = COALESCE(metadata, '{}'::jsonb) ||
    '{"performer_overrides":{"Andre De Freitas":["André de Freitas"],"Jerry Wayne Longmire":["Jerry Wayne Longmire"],"One Funny Lisa Marie":["Lisa Marie"],"Sarper Guven":["Sarper Güven"]}}'::jsonb,
    updated_at = NOW()
WHERE club_id = 217 AND platform = 'custom' AND priority = 0
  AND scraper_key = 'comedy_connection';
