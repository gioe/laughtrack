-- TASK-558: Add Improv Asylum as a new venue
-- Improv Asylum is a Boston comedy club at 216 Hanover St in the North End.
-- Shows are listed on their Tixr group page (tixr.com/groups/improvasylum).
-- Scraper fetches the Tixr group page, extracts event URLs, and uses TixrClient.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Improv Asylum',
    '216 Hanover St',
    'Boston',
    'MA',
    '02113',
    'America/New_York',
    'improv_asylum',
    TRUE,
    'https://improvasylum.com',
    'https://www.tixr.com/groups/improvasylum'
);
