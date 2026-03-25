-- TASK-682: Add Laugh Factory Covina as a new venue
-- Website: https://www.laughfactory.com/covina (redirects to Tixr group page)
-- Laugh Factory Covina is located at 104 N Citrus Ave, Covina, CA 91723.
-- Shows are sold through Tixr (tixr.com/groups/laughfactorycovina).
-- Scraper fetches the Tixr group page, extracts event URLs, and uses TixrClient.

INSERT INTO clubs (name, address, city, state, zip_code, timezone, scraper, visible, website, scraping_url)
VALUES (
    'Laugh Factory Covina',
    '104 N Citrus Ave',
    'Covina',
    'CA',
    '91723',
    'America/Los_Angeles',
    'laugh_factory_covina',
    TRUE,
    'https://www.laughfactory.com/covina',
    'https://www.tixr.com/groups/laughfactorycovina'
);
