-- Update Bushwick Comedy Club scraping_url to new domain.
-- The old domain www.bushwickcomedyclub.com expired and redirects to an unrelated venue (The Tiny Cupboard).
-- The club has moved to www.bushwickcomedy.com.
UPDATE clubs
SET scraping_url = 'https://www.bushwickcomedy.com'
WHERE scraper = 'bushwick'
  AND scraping_url LIKE '%bushwickcomedyclub.com%';
