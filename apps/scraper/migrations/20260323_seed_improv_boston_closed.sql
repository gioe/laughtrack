-- TASK-589: Seed ImprovBoston as the first closed venue record
-- ImprovBoston closed permanently in 2020 (COVID-related closure).
-- Inserting as status='closed' prevents re-discovery and scrape attempts.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url, status, closed_at)
VALUES (
    'ImprovBoston',
    '40 Prospect St',
    'Cambridge',
    'MA',
    '02139',
    'America/New_York',
    NULL,
    FALSE,
    'https://www.improvboston.com',
    '',
    'closed',
    '2020-03-13 00:00:00+00'
)
-- ON CONFLICT relies on the existing UNIQUE constraint on clubs.name
ON CONFLICT (name) DO UPDATE SET
    status    = 'closed',
    closed_at = COALESCE(clubs.closed_at, EXCLUDED.closed_at);
