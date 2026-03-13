-- Set email scraper keys on Gotham and Comedy Cellar club records
-- to activate email-based show ingestion via GothamEmailScraper and ComedyCellarEmailScraper.
DO $$
BEGIN
    -- Gotham Comedy Club: set scraper='gotham_email' (idempotent: skip if already set)
    UPDATE "clubs" SET scraper = 'gotham_email'
    WHERE name = 'Gotham Comedy Club' AND scraper IS DISTINCT FROM 'gotham_email';
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Gotham Comedy Club') THEN
        RAISE EXCEPTION 'Club "Gotham Comedy Club" not found — check clubs.name matches exactly.';
    END IF;

    -- Comedy Cellar: set scraper='comedy_cellar_email' (idempotent: skip if already set)
    UPDATE "clubs" SET scraper = 'comedy_cellar_email'
    WHERE name = 'Comedy Cellar New York' AND scraper IS DISTINCT FROM 'comedy_cellar_email';
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = 'Comedy Cellar New York') THEN
        RAISE EXCEPTION 'Club "Comedy Cellar New York" not found — check clubs.name matches exactly.';
    END IF;
END $$;
