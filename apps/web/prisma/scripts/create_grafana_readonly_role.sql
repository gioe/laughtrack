-- One-off operational script: create a least-privilege read-only role for Grafana Cloud.
--
-- Grafana Cloud connects to Neon as a dedicated `grafana_ro` role — NOT the application's
-- DB role — with SELECT limited to the observability tables only (scraper_runs,
-- scraper_run_clubs, scraper_run_errors, api_request_metrics). There is no blanket schema
-- grant, so the role cannot read users, sessions, or any other table even if the
-- datasource is misconfigured.
--
-- Run manually against the Neon production database when onboarding Grafana:
--   psql "$DIRECT_URL" -f prisma/scripts/create_grafana_readonly_role.sql
--
-- After running, set the role's password out-of-band (do NOT commit it):
--   ALTER ROLE grafana_ro WITH PASSWORD '<generated-password>';
--
-- Then point Grafana's Postgres datasource at the POOLED Neon endpoint (hostname ends in
-- `-pooler.`, matching DATABASE_URL) with sslmode=require. See apps/web/DEPLOYMENT.md →
-- "Database Observability (Grafana Cloud)".
--
-- Idempotent: re-running is safe — the role is created only if absent and grants are additive.
DO $$
BEGIN
    -- Create the login role if it doesn't already exist.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_ro') THEN
        CREATE ROLE grafana_ro WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
        RAISE NOTICE 'Created role grafana_ro. Set its password with: ALTER ROLE grafana_ro WITH PASSWORD ''<generated>'';';
    ELSE
        RAISE NOTICE 'Role grafana_ro already exists — skipping CREATE ROLE.';
    END IF;

    -- Allow the role to connect to the database this script is run against
    -- (current_database() avoids hardcoding the environment-specific DB name).
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO grafana_ro', current_database());

    -- Self-heal least privilege: strip any pre-existing blanket grants (e.g. a manual
    -- GRANT SELECT ON ALL TABLES) before re-granting only the scraper-health tables.
    -- Without this, the grants below are purely additive and an over-granted role
    -- (able to read users, refresh_tokens, etc.) would silently stay over-granted.
    REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM grafana_ro;
    REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM grafana_ro;

    -- Schema access + SELECT on ONLY the observability tables (least privilege):
    -- the three scraper-health tables plus the per-route API request counter.
    GRANT USAGE ON SCHEMA public TO grafana_ro;
    GRANT SELECT ON
        public.scraper_runs,
        public.scraper_run_clubs,
        public.scraper_run_errors,
        public.api_request_metrics
        TO grafana_ro;
END $$;
