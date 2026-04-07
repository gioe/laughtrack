-- TASK-1006: Add McCurdy's Comedy Theatre as a new venue
-- Website: https://www.mccurdyscomedy.com
-- McCurdy's Comedy Theatre (1923 Ringling Blvd, Sarasota, FL) has been
-- operating since 1988 in downtown Sarasota.  Shows run Wed–Sun.
-- Custom ColdFusion site; tickets sold through Etix (etix.com/ticket/v/16715).

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url, phone_number)
VALUES (
    'McCurdy''s Comedy Theatre',
    '1923 Ringling Blvd',
    'Sarasota',
    'FL',
    '34236',
    'America/New_York',
    'mccurdys_comedy_theatre',
    TRUE,
    'https://www.mccurdyscomedy.com',
    'https://www.mccurdyscomedy.com/shows/',
    '941-925-3869'
);
