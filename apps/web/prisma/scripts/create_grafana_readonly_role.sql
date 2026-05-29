-- One-off operational script: create a least-privilege read-only role for Grafana Cloud.
--
-- Grafana Cloud connects to Neon as a dedicated `grafana_read` role — NOT the application's
-- DB role — with SELECT limited to the scraper-health tables only (scraper_runs,
-- scraper_run_clubs, scraper_run_errors). There is no blanket schema grant, so the role
-- cannot read users, sessions, or any other table even if the datasource is misconfigured.
--
-- Run manually against the Neon production database when onboarding Grafana:
--   psql "$DIRECT_URL" -f prisma/scripts/create_grafana_readonly_role.sql
--
-- After running, set the role's password out-of-band (do NOT commit it):
--   ALTER ROLE grafana_read WITH PASSWORD '<generated-password>';
--
-- Then point Grafana's Postgres datasource at the POOLED Neon endpoint (hostname ends in
-- `-pooler.`, matching DATABASE_URL) with sslmode=require. See apps/web/DEPLOYMENT.md →
-- "Database Observability (Grafana Cloud)".
--
-- Idempotent: re-running is safe — the role is created only if absent and grants are additive.
DO $$
BEGIN
    -- Create the login role if it doesn't already exist.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_read') THEN
        CREATE ROLE grafana_read WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
        RAISE NOTICE 'Created role grafana_read. Set its password with: ALTER ROLE grafana_read WITH PASSWORD ''<generated>'';';
    ELSE
        RAISE NOTICE 'Role grafana_read already exists — skipping CREATE ROLE.';
    END IF;

    -- Allow the role to connect to the database this script is run against
    -- (current_database() avoids hardcoding the environment-specific DB name).
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO grafana_read', current_database());

    -- Schema access + SELECT on ONLY the three scraper-health tables (least privilege).
    GRANT USAGE ON SCHEMA public TO grafana_read;
    GRANT SELECT ON
        public.scraper_runs,
        public.scraper_run_clubs,
        public.scraper_run_errors
        TO grafana_read;
END $$;
