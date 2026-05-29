# Grafana dashboards (scraper-health)

Dashboard-as-code for the scraper-health Postgres tables (`scraper_runs`,
`scraper_run_clubs`, `scraper_run_errors`), which the scraper writes after every run but
which nothing read until now.

## Files

- `scraper-health.json` — the **Scraper Health** dashboard. Panels:
  - Run success-rate over time
  - Per-club success-rate trend
  - Run duration
  - Error count by run (over time)
  - Clubs dropped to zero shows (latest run)
  - Bot-block providers (error counts by type)

## One-time setup

1. **Create the read-only Neon role** (least-privilege; SELECT only on the three
   scraper-health tables):

   ```bash
   psql "$DIRECT_URL" -f apps/web/prisma/scripts/create_grafana_readonly_role.sql
   psql "$DIRECT_URL" -c "ALTER ROLE grafana_ro WITH PASSWORD '<generated-password>';"
   ```

2. **Add the Postgres datasource in Grafana Cloud** — point it at the **pooled** Neon
   endpoint (hostname ends in `-pooler.`) with the `grafana_ro` credentials and
   `sslmode=require`. "Save & Test" must pass.

3. **Import the dashboard** — Grafana → Dashboards → New → Import → upload
   `scraper-health.json` → select the Neon datasource for the `${datasource}` variable.

Full operator walkthrough lives in `apps/web/DEPLOYMENT.md` →
**Database Observability (Grafana Cloud)**.

## Editing

The dashboard is plain Grafana JSON. Edit panels in the Grafana UI, then export
(Dashboard settings → JSON Model, or Share → Export → "Export for sharing externally"
off) and overwrite `scraper-health.json` so the repo stays the source of truth.
