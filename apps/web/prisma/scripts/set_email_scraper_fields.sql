-- One-off data script: set email scraper keys on Gotham and Comedy Cellar club records.
-- Extracted from migration 20260308000000_set_email_scraper_fields to keep the migration
-- idempotent on a clean database (shadow DB safe).
--
-- Run manually against the Neon production database when needed:
--   psql $DIRECT_URL -f prisma/scripts/set_email_scraper_fields.sql
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
