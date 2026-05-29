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
- `scraper-health-alerts.yaml` — unified-alerting **rules-as-code** that baseline
  each run against the trailing-N-run rolling average and fire to Discord on a
  regression (see **Regression alerts** below).

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

## Regression alerts

`scraper-health-alerts.yaml` defines three unified-alerting rules. Each compares
the **latest run** against the **trailing 7-run rolling average** (rows
`rn BETWEEN 2 AND 8` in the SQL — widen/narrow by editing those bounds) and
routes to a Discord contact point:

1. **Success-rate regression** — fires when the latest run's overall
   `scraper_runs.success_rate` is more than 10 percentage points below the
   trailing average.
2. **Club dropped to zero shows** — fires when a club returned shows in the
   previous run but zero in the latest run. The query matches the *transition*
   (prev > 0, latest = 0), so it fires **exactly once** per drop: on the next run
   the previous run is itself zero, the condition no longer holds, and the alert
   resolves. One alert instance per club (the `club` label).
3. **Error-count spike** — fires when the latest run logged more than 5 errors
   above the trailing-average error count.

These replace the scraper's old unconditional per-run Discord summary (gated off
in TASK-2511): a healthy run produces no Discord post, so Discord carries only
failures and regressions.

### Setup

1. **Pin the datasource UID.** The rule file references the Neon datasource by
   the UID `neon-scraper-health`. Either set the datasource's UID to that value
   (datasource settings → JSON model) or replace every `neon-scraper-health`
   occurrence in the YAML with your datasource's actual UID.
2. **Set the Discord webhook.** Replace `REPLACE_WITH_DISCORD_WEBHOOK_URL` in the
   `contactPoints` block with the `#laughtrack` channel's incoming-webhook URL
   (do **not** append `/slack`). Keep the secret out of git.
3. **Provision the rules.**
   - *Self-hosted Grafana:* drop `scraper-health-alerts.yaml` in
     `/etc/grafana/provisioning/alerting/` and restart.
   - *Grafana Cloud* (no file provisioning): recreate the three rules via
     **Alerting → Alert rules → New** using the SQL and thresholds from the file
     verbatim, or apply them with Terraform / the Alerting API.
4. **Route to Discord.** Provisioned notification `policies` replace the org root
   policy, so the YAML leaves that block commented out. Add a notification-policy
   route in the UI instead: matcher `service = scraper-health` → contact point
   `scraper-health-discord`.

## Editing

The dashboard is plain Grafana JSON. Edit panels in the Grafana UI, then export
(Dashboard settings → JSON Model, or Share → Export → "Export for sharing externally"
off) and overwrite `scraper-health.json` so the repo stays the source of truth.
