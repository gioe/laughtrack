-- TASK-671: Seed The Comedy Union as a permanently closed venue
-- The Comedy Union (first Black-owned comedy club in LA) closed permanently
-- during COVID-19 and did not reopen. Website (thecomedyunion.com) returns 404.
-- Yelp status: CLOSED (updated January 2026).
-- Inserting as status='closed' prevents re-discovery and scrape attempts.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url, status, closed_at)
VALUES (
    'The Comedy Union',
    '5040 W Pico Blvd',
    'Los Angeles',
    'CA',
    '90019',
    'America/Los_Angeles',
    NULL,
    FALSE,
    'https://thecomedyunion.com',
    '',
    'closed',
    '2020-01-01 00:00:00+00'
)
ON CONFLICT (name) DO UPDATE SET
    status    = 'closed',
    closed_at = COALESCE(clubs.closed_at, EXCLUDED.closed_at);
