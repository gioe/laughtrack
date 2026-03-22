-- TASK-559: Add Nick's Comedy Stop as a new venue
-- Nick's Comedy Stop is a comedy club at 100 Warrenton St, Boston, MA.
-- Shows are listed via Wix Events (native ticketing) on their homepage.
-- Scraper fetches the Wix Events API using the events widget compId.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Nick''s Comedy Stop',
    '100 Warrenton St',
    'Boston',
    'MA',
    '02116',
    'America/New_York',
    'nicks_comedy_stop',
    TRUE,
    'https://www.nickscomedystop.com',
    'https://www.nickscomedystop.com'
);
