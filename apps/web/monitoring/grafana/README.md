# Grafana dashboards (scraper-health)

Dashboard-as-code for the scraper-health Postgres tables (`scraper_runs`,
`scraper_run_clubs`, `scraper_run_errors`), which the scraper writes after every run but
which nothing read until now.

`scraper_runs` is shared by three writers, discriminated by `run_type`:

- `run_type = 'scraper'` — real **full** scrape snapshots (the nightly
  `scrape_shows --all`), carrying per-club child rows. These are the only runs the
  dashboard panels and alert windows are designed to compare.
- `run_type = 'pipeline'` — generic GitHub Actions pipeline records (no child rows,
  synthetic `success_rate`), written by `record_pipeline_run.py` /
  `backfill_github_pipeline_runs.py`.
- `run_type = 'verify'` — single-club verify runs (`scrape_shows --club-id`/`--club`),
  with `clubs_processed = 1`. Because they hold child rows for only one club, leaving
  them tagged `'scraper'` made a verify run landing as rn=1/rn=2 between two nightlies
  silently mask a zero-drop for every _other_ club (root cause of the missed ImprovCity
  alert — TASK-2824 / TASK-2831), and skewed the success-rate / error-count baselines.

Every dashboard panel and alert comparison window filters on `run_type = 'scraper'`,
so both pipeline and verify rows are excluded from the scraper metrics automatically.
(This filter replaced the earlier `run_key LIKE 'scraper:%'` naming-convention
discriminator — TASK-2518.) The one deliberate exception is rule 4's 30-day `history`
lookback, which matches `run_type IN ('scraper', 'verify')`: a recent single-club
verify scrape that returned shows is still valid evidence the club is not dark.

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
- `api-requests.json` — the **API Requests** dashboard, reading the
  `api_request_metrics` hourly counter table (written by the `withRequestMetrics`
  handler wrapper). Panels:

  - Requests per route over time
  - Top routes by volume
  - Requests by status_class over time
  - Requests by HTTP method

  Unlike `scraper-health.json` (which uses a `${datasource}` template variable),
  this dashboard pins the Neon datasource UID `dfnjxqagicw74a` directly — the same
  UID the regression alerts reference — so importing it requires no variable
  selection. If the datasource is recreated under a new UID, replace every
  `dfnjxqagicw74a` occurrence in the JSON. Import the same way:
  Grafana → Dashboards → New → Import → upload `api-requests.json`.

- `youtube-websub.json` — the **YouTube WebSub** dashboard. Panels:

  - WebSub callbacks received by event status over time
  - Subscription renewal failures plus oldest expiring active lease
  - YouTube Data API verification outcomes by status
  - YouTube live push delivery counts for sent, failed, and suppressed events

  Import it like `scraper-health.json`: Grafana → Dashboards → New → Import →
  upload `youtube-websub.json` → select the Neon datasource for the `${datasource}`
  variable.

## One-time setup

1. **Create the read-only Neon role** (least-privilege; SELECT only on the
   scraper/API/WebSub observability tables):

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

`scraper-health-alerts.yaml` defines five unified-alerting rules routed to a
Discord contact point. Rules 1 and 3 compare the **latest run** against the
**trailing 7-run rolling average** (rows `rn BETWEEN 2 AND 8` in the SQL —
widen/narrow by editing those bounds):

1. **Success-rate regression** — fires when the latest run's overall
   `scraper_runs.success_rate` is more than 10 percentage points below the
   trailing average.
2. **Club dropped to zero shows** — fires when a club returned shows in the
   previous run but zero in the latest run. The firing condition matches the
   _transition_ (prev > 0, latest = 0), so it fires **exactly once** per drop: on
   the next run the previous run is itself zero, the condition no longer holds,
   and the alert resolves. Since TASK-2834 the backing view retains a fired
   club's series (0-valued) for one extra run, so the resolution is a
   **Normal** state change rather than a MissingSeries vanish — Discord no
   longer receives `grafana_state_reason=MissingSeries` churn. One alert
   instance per club (the `club` and `club_id` labels; `club_id` feeds the
   Discord template's `scraper-verify` next step).
3. **Error-count spike** — fires when the latest run logged more than 5 errors
   above the trailing-average error count.
4. **Club at zero shows for 2+ consecutive full runs** — self-healing companion
   to rule 2 (TASK-2832). Fires when a club has zero shows in the last 2
   consecutive **full** scrape runs (`clubs_processed > 1`, so single-club
   verify runs cannot pollute the comparison window — the TASK-2824 ImprovCity
   miss) but had shows within the trailing 30 days. Unlike the one-shot
   transition rule, this condition **keeps firing every evaluation until the
   club recovers**, so a missed evaluation cannot bury an outage. The 30-day
   `> 0` lookback keeps legitimately dark venues (clubs that never had shows)
   out of the alert; a club that genuinely goes dark stops firing 30 days
   after its last show. One alert instance per club (the `club` and `club_id`
   labels). Like rule 2, the backing view retains a fired club's series
   (0-valued) for one extra run (TASK-2834), so a recovery resolves as Normal —
   a Discord "Resolved" post on this rule genuinely means shows came back.
5. **Pipeline liveness / staleness** (TASK-3040) — fires when the newest full
   scrape run (`scraper_runs.run_type='scraper'`) is more than 26 hours old.
   Unlike rules 1–4, which baseline the latest run against prior runs and go
   silent when the pipeline fails to run **at all** (no new row → "latest" never
   advances), this rule is failure-mode-agnostic: it catches a pre-scrape
   migrate/setup failure, a disabled schedule, or a hung job. Its `noDataState`
   is **Alerting** (not `OK`): an empty `scraper_runs` table is itself an outage
   signal. (Motivated by the TASK-3036 incident: a bad onboarding migration
   failed the pre-scrape migrate step and silently skipped ~4 nightly runs with
   no alert.) The GHA `Notify on failure` step (`scraper-schedule.yml`) also now
   posts to Discord on a hard job failure as an immediate same-run signal.

These replace the scraper's old unconditional per-run Discord summary (gated off
in TASK-2511): a healthy run produces no Discord post, so Discord carries only
failures and regressions.

The alert group intentionally evaluates every **6 hours**, not hourly. The
nightly scraper runs once per day at 21:00 UTC, and most regression rules only
change when a new `scraper_runs` row lands. Six-hour evaluation keeps multiple
checks per day and still lets the 26-hour staleness rule fire after a missed
nightly run, while avoiding thousands of redundant Postgres reads that keep the
Neon compute warm. The dashboard JSON also leaves `"refresh": ""` so opening
the Scraper Health dashboard does not start an automatic polling loop; refresh
manually during an investigation.

### Precomputed summary views (TASK-3573)

Rules 1, 2, 4, and 3 previously recomputed their last-two-run / trailing-window /
30-day-`history` CTEs against `scraper_runs` + `scraper_run_clubs` on **every**
evaluation, even though the underlying data changes only once per nightly scrape.
(This is complementary to the 6-hour cadence above: the cadence cuts how often
the SQL runs, the views cut how expensive each run is.) They now `SELECT` from
three small **materialized views** that the scraper refreshes once at the end of
each full `scraper` run:

- `mv_scraper_health_overall` — one row: `success_rate_drop` (rule 1) and
  `error_spike` (rule 3), both vs the trailing-7-run average.
- `mv_scraper_health_dropped_to_zero` — one row per club whose prev>0 →
  latest=0 transition held in the latest run (`dropped_to_zero` = 1) **or the
  previous run** (0 — one-extra-run series retention so the recovery resolves
  as Normal), plus a `club_id` label (rule 2).
- `mv_scraper_health_consecutive_zero` — one row per club that was at zero for
  2+ consecutive full runs, had shows in the last 30 days, and has an active
  regression signal: the latest/previous run failed, the latest/previous run
  detected a bot block, or the DB still has future shows for the club. Rows are
  emitted for clubs matching that condition as of the latest run
  (`consecutive_zero` = 1) **or the previous run** (0), plus a `club_id` label
  (rule 4). The active-signal filter was added in TASK-3584 after live triage
  showed cleanly empty aggregate Ticketmaster/Eventbrite one-off listings
  dominating the alert. Deliberately not one-row-per-club: Grafana's alert
  evaluator caps a query at 1000 series and the latest run spans ~1,559 clubs.

The original materialized-view definitions used the exact CTEs the rules used to
inline, so alerts only changed state when a new run landed, which is precisely
when the refresh runs. TASK-3584 intentionally narrows the consecutive-zero
semantics, but the same run-refresh cadence still applies. The original DDL lives in
`apps/scraper/migrations/20260703_scraper_health_summary_materialized_views.sql`;
`20260704_scraper_health_club_labels_stable_series.sql` (TASK-2834) recreates the
two club-level views with the `club_id` label and the one-extra-run series
retention; `20260706174000_retune_consecutive_zero_health_alert.sql` (TASK-3584)
recreates only the consecutive-zero view with the active-regression-signal
filter. These are applied by `apps/scraper/bin/migrate`. The refresh is
`PostgresMetricsRepository.refresh_health_summary()`, called after each `scraper`
run persists. **Rule 5 (staleness) stays a live inline query** — it measures
`NOW() - MAX(exported_at)` and must not be frozen at run time. If the pipeline
stops running, the views go stale but rule 5 still fires (it does not read them).

The migrations grant `SELECT` on the views to `grafana_ro`
(`GRANT ... ON ALL TABLES` does not cover materialized views, so they are granted
by name — the same list is mirrored in `create_grafana_readonly_role.sql`; note a
`DROP MATERIALIZED VIEW` discards grants, so recreation migrations must re-grant).

### Setup

1. **Pin the datasource UID.** The rule file references the Neon datasource by
   the UID `dfnjxqagicw74a` (the real, immutable UID of the `grafana_ro` Neon
   datasource in the aiqobservability stack — same value the dashboard JSON pins,
   see above). If the datasource is ever recreated, replace every
   `dfnjxqagicw74a` occurrence in the YAML with the new UID.
2. **Set the Discord webhook.** Replace `REPLACE_WITH_DISCORD_WEBHOOK_URL` in the
   `contactPoints` block with the `#laughtrack` channel's incoming-webhook URL
   (do **not** append `/slack`). Keep the secret out of git.
3. **Provision the rules.**

   - _Self-hosted Grafana:_ drop `scraper-health-alerts.yaml` in
     `/etc/grafana/provisioning/alerting/` and restart.
   - _Grafana Cloud_ (no **file** provisioning): **automated on merge**
     (TASK-3580). The `Provision Grafana Alert Rules` GitHub Actions workflow
     (`.github/workflows/grafana-provision.yml`) runs
     `provision_alert_rules.py` on every merge to `main` that touches the
     YAML (or the script), reconciling the rules into the aiqobservability
     stack via the Alerting provisioning HTTP API using the
     `GRAFANA_ACCOUNT_TOKEN` repo secret. The reconcile is idempotent (no-op
     when already in sync), matches live rules by uid then by exact title
     (the pre-automation rules were created in the UI with random uids), and
     manages the rule fields the YAML owns (title, condition, query chain,
     states, `for`, labels, annotations) plus the group evaluation interval —
     while preserving Grafana-side state (live uid, folder, contact-point
     binding, server-added query-model defaults). Rules present in the YAML
     but missing in Grafana Cloud are created (contact-point binding copied
     from a sibling rule in the group). `contactPoints`/`policies` blocks are
     **not** reconciled — see the YAML comments.

     To run it by hand (drift check or ad-hoc sync — the token lives in
     `apps/scraper/.env`):

     ```bash
     # From the repo root; --dry-run reports drift without writing.
     GRAFANA_ACCOUNT_TOKEN=... \
       python3 apps/web/monitoring/grafana/provision_alert_rules.py --dry-run
     ```

     The workflow also supports manual `workflow_dispatch` (with a dry-run
     input) from the Actions tab.

4. **Apply the Discord message template (manual — not auto-provisioned).** The
   YAML's `templates` block defines `scraper_health.discord.message` (TASK-2834):
   it leads with the club or alert name, includes the rule's
   summary/description annotations, and renders a concrete next step —
   `dispatch scraper-verify for club_id=NNN` when the alert carries the
   `club_id` label. The grafana-provision workflow reconciles **alert rules
   only**; templates and contact points must be kept in sync by hand. In
   Grafana Cloud: **Alerting → Contact points → the Discord contact point →
   Message** — set it to `{{ template "scraper_health.discord.message" . }}`
   and mirror any template-body change under **Alerting → Notification
   templates** (template `scraper-health-discord-message`, created 2026-06-12).
   Without the annotations + template, Discord falls back to raw
   Alertmanager label dumps.
5. **Route to Discord.** Provisioned notification `policies` replace the org root
   policy, so the YAML leaves that block commented out. Add a notification-policy
   route in the UI instead: matcher `service = scraper-health` → contact point
   `scraper-health-discord`.
6. **Keep genuine recoveries, suppress churn.** Leave Discord resolved messages
   enabled (`disableResolveMessage: false`): genuine recoveries should post, but
   NoData/MissingSeries churn should not. The regression rules set
   `noDataState: OK`, and since TASK-2834 the club-level views retain a fired
   club's series (0-valued) for one extra run, so recoveries resolve as Normal
   rather than MissingSeries. If Discord still shows
   `grafana_state_reason=NoData` or `MissingSeries` resolved posts, check that
   the Cloud SQL matches the YAML (run the provision script with `--dry-run`)
   before reaching for `disableResolveMessage: true` — disabling all resolved
   messages hides real recoveries.

## Editing

The dashboard is plain Grafana JSON. Edit panels in the Grafana UI, then export
(Dashboard settings → JSON Model, or Share → Export → "Export for sharing externally"
off) and overwrite `scraper-health.json` so the repo stays the source of truth.
