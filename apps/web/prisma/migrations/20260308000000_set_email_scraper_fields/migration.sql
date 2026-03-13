-- Set email scraper keys on Gotham and Comedy Cellar club records.
-- Data-seed step extracted to prisma/scripts/set_email_scraper_fields.sql
-- so this migration is idempotent on a clean (shadow) database.
UPDATE "clubs" SET scraper = 'gotham_email'
WHERE name = 'Gotham Comedy Club' AND scraper IS DISTINCT FROM 'gotham_email';

UPDATE "clubs" SET scraper = 'comedy_cellar_email'
WHERE name = 'Comedy Cellar New York' AND scraper IS DISTINCT FROM 'comedy_cellar_email';
