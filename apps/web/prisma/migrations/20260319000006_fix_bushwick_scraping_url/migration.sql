-- Fix Bushwick Comedy Club scraping_url: the previous migration's WHERE clause
-- did not match because the stored URL was 'bushwickcomedy.com/...' (no protocol,
-- different path). Set the clean base URL with protocol for the scraper to use.
UPDATE clubs
SET scraping_url = 'https://www.bushwickcomedy.com'
WHERE scraper = 'bushwick';
