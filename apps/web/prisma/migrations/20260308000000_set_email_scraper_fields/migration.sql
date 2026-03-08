-- Set email scraper keys on Gotham and Comedy Cellar club records
-- to activate email-based show ingestion via GothamEmailScraper and ComedyCellarEmailScraper.
UPDATE "clubs" SET scraper = 'gotham_email' WHERE name = 'Gotham Comedy Club';
UPDATE "clubs" SET scraper = 'comedy_cellar_email' WHERE name = 'Comedy Cellar';
