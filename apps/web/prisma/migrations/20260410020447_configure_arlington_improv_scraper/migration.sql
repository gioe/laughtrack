-- Configure Arlington Improv (club 39) to use the improv scraper
-- The club already exists but has no scraper configured (scraper=NULL, scraping_url='improvtx/comedians')
-- Same platform as Addison Improv (improvtx.com), which uses the improv scraper successfully
UPDATE "clubs"
SET
    scraper = 'improv',
    scraping_url = 'improvtx.com/arlington/calendar/',
    address = '309 Curtis Mathes Way #147',
    city = 'Arlington',
    state = 'TX',
    zip_code = '76018',
    timezone = 'America/Chicago'
WHERE id = 39
  AND name = 'Arlington Improv';
