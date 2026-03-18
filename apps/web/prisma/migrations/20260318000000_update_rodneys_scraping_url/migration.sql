-- Update Rodney's Comedy Club scraping_url to new domain.
-- The old domain tickets.rodneycomedy.com no longer resolves (DNS failure).
-- The club has moved to rodneysnewyorkcomedyclub.com and the calendar is at /calendar.
UPDATE clubs
SET scraping_url = 'rodneysnewyorkcomedyclub.com/calendar'
WHERE scraper = 'rodneys'
  AND scraping_url LIKE '%rodneycomedy.com%';
