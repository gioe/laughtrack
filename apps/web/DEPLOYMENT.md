# LaughTrack Web App — Production Deployment Guide

This document covers everything a new engineer needs to deploy the web app from scratch.

---

## Prerequisites

- Node.js 20+
- A [Neon](https://neon.tech) PostgreSQL project (or compatible hosted Postgres)
- A [Vercel](https://vercel.com) account (or Google Cloud Run)
- A [Bunny CDN](https://bunny.net) pull zone for comedian images
- Google OAuth credentials
- Apple Sign In credentials (optional — see below)
- An SMTP provider (Gmail, SendGrid, Postmark, etc.)

---

## Environment Variables

Copy `.env.example` to `.env.local` for local development, or add these to your hosting provider's environment configuration for production.

### Database (Required)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Neon connection URL used by Prisma at runtime. Use the **pooled** Neon endpoint (the one whose hostname ends in `-pooler.`). Do **not** append `?pgbouncer=true` — this project uses `@prisma/adapter-neon` with the WebSocket protocol, which connects directly to the Neon compute endpoint, bypassing PgBouncer entirely. |
| `DIRECT_URL` | Yes | **Non-pooled** Neon connection URL (direct endpoint, no `-pooler.` in the hostname). Required for `prisma migrate deploy` to work. |

> **Important:** `DIRECT_URL` must be the **non-pooled** Neon URL. Prisma uses this URL when running migrations — the pooled endpoint blocks the advisory locks that migration tracking requires.

In the Neon dashboard, find both URLs under **Connection Details**:
- Pooled endpoint → `DATABASE_URL`
- Direct endpoint → `DIRECT_URL`

> **Note on `?pgbouncer=true`:** This parameter is only for the Prisma HTTP/PgBouncer connection mode. This project uses `@prisma/adapter-neon` with `@neondatabase/serverless` (WebSocket), which is not subject to PgBouncer's transaction-mode restrictions. Do not add `?pgbouncer=true` to either URL.

### Authentication (Required)

| Variable | Required | Description |
|---|---|---|
| `AUTH_SECRET` | Yes | Random secret used to sign session tokens. Generate with: `openssl rand -base64 32`. **Rotating this secret invalidates all active user sessions immediately.** NextAuth v5 uses `AUTH_SECRET` as the canonical name; `NEXTAUTH_SECRET` is supported as a legacy alias but may be dropped in a future release. |
| `AUTH_URL` | Yes (Cloud Run) / No (Vercel) | Canonical URL of the app (e.g. `https://laughtrack.com`). Required on Cloud Run where the host cannot be inferred from the request. On Vercel, NextAuth v5 auto-detects the URL from `VERCEL_URL`. Use `http://localhost:3000` locally. |
| `AUTH_GOOGLE_ID` | Yes | Google OAuth client ID. Create credentials at [console.cloud.google.com](https://console.cloud.google.com). |
| `AUTH_GOOGLE_SECRET` | Yes | Google OAuth client secret. |
| `AUTH_APPLE_ID` | No | Apple Sign In service ID. Added post-TASK-91. See setup instructions below. Both `AUTH_APPLE_ID` and `AUTH_APPLE_SECRET` must be set together — the Apple provider is always registered in `auth.ts` and will fail at sign-in if either var is missing. |
| `AUTH_APPLE_SECRET` | No | Apple Sign In generated client-secret JWT. Added post-TASK-91. |

#### Generating AUTH_SECRET

```bash
openssl rand -base64 32
```

> **Operational note:** `AUTH_SECRET` and `SECRET_KEY` must be identical across all running instances (e.g. multiple Cloud Run revisions or Vercel preview deployments sharing the same Neon DB). Changing `AUTH_SECRET` in production will immediately log out all users.

#### Apple Sign In Setup (AUTH_APPLE_ID / AUTH_APPLE_SECRET)

Apple OAuth credentials were added in TASK-91 and are optional — the app works without them (Google and magic-link email sign-in remain available). However, if either variable is absent, the Apple sign-in button will appear but fail.

To enable Apple Sign In:

1. Go to [developer.apple.com](https://developer.apple.com) → Certificates, Identifiers & Profiles
2. Create a **Services ID** (this becomes `AUTH_APPLE_ID`)
3. Create a **Key** with Sign In with Apple enabled, download the `.p8` file
4. Generate the Apple client-secret JWT and store that value in `AUTH_APPLE_SECRET`:
   ```bash
   npx auth add apple
   ```
   > **Warning:** Do not store the raw `.p8` private key in `AUTH_APPLE_SECRET`. Auth.js expects the generated client-secret JWT. Test Apple auth end-to-end in staging before relying on it in production.
5. Add the OAuth redirect URL `https://your-domain.com/api/auth/callback/apple` to the Services ID configuration

### Email / Magic-Link Sign-In (Required in Production)

Without SMTP credentials, the email magic-link provider fails at startup in production. Configure any SMTP provider:

| Variable | Required | Description |
|---|---|---|
| `SMTP_HOST` | Yes | SMTP server hostname (e.g. `smtp.gmail.com`, `smtp.sendgrid.net`) |
| `SMTP_PORT` | Yes | SMTP port — `587` for STARTTLS (recommended), `465` for SSL |
| `SMTP_USER` | Yes | SMTP account username (usually an email address) |
| `SMTP_PASSWORD` | Yes | SMTP password or app-specific password |
| `SMTP_SECURE` | Yes | `"true"` for port 465 (SSL), `"false"` for port 587 (STARTTLS) |
| `EMAIL_FROM` | Yes | "From" address shown in magic-link emails (e.g. `noreply@laughtrack.com`) |

For Gmail, create an **App Password** at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) — do not use your regular Gmail password.

### CDN (Required)

| Variable | Required | Description |
|---|---|---|
| `BUNNYCDN_CDN_HOST` | Yes | Hostname of your Bunny CDN pull zone (e.g. `laughtrack.b-cdn.net`). Used to serve comedian images. |

### Security (Required)

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Secret used to sign JWT tokens (e.g. unsubscribe links). Generate with: `openssl rand -base64 32` |

### Public App Config (Required)

> **Build-time requirement:** Variables prefixed with `NEXT_PUBLIC_` are statically inlined into the JavaScript bundle at build time by Next.js. They **must** be set in the build environment (e.g. as Vercel build-time env vars), not only as runtime secrets. If set only at runtime, they will be `undefined` in all client-side code.

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_WEBSITE_URL` | Yes | Canonical URL of the site (e.g. `https://laughtrack.com`). Used for absolute URLs and OG meta tags. **Must be a build-time env var** — see note above. |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated list of allowed CORS origins. Defaults to `NEXT_PUBLIC_WEBSITE_URL` if not set. |

### Error Tracking (Optional)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_SENTRY_DSN` | No | Sentry DSN from your project's Client Keys page. Leave empty in development. **Must be a build-time env var** — this value is inlined at build time into server, edge, and client Sentry configs. Setting it only as a runtime secret will result in Sentry being silently disabled. |

### Storage (Optional)

| Variable | Required | Description |
|---|---|---|
| `DIRECTORY_PATH` | No | Absolute path to a local directory for file storage (e.g. `/tmp/laughtrack`). Not required in Cloud Run or Vercel deployments where this path is unused. |

### Cloud Run (Auto-Set)

| Variable | Required | Description |
|---|---|---|
| `K_REVISION` | Auto | Set automatically by Google Cloud Run. Used to detect cloud environment. Do **not** set this manually. |

---

## Running Migrations

> **Important:** `prisma migrate dev` cannot be used in **any** environment (local or production) in this project. The shadow database validation fails on a migration that requires existing data (`Gotham Comedy Club` must exist). Always use `prisma migrate deploy`.
>
> For new migrations: write the SQL manually, create the directory `prisma/migrations/<timestamp>_<name>/migration.sql`, update `prisma/schema.prisma`, and commit both files. Then run `prisma migrate deploy` to apply.

```bash
cd apps/web
npx prisma migrate deploy
```

Ensure `DATABASE_URL` and `DIRECT_URL` are set in the environment before running. `DIRECT_URL` must point to the non-pooled Neon endpoint.

> **Migration timing:** Always run `prisma migrate deploy` **before** the new app version goes live. On Vercel, add it as a build command (`npx prisma migrate deploy && next build`) or run it manually before triggering a deploy. Deploying the new code before the schema is updated will cause runtime errors.

### Post-Migration: Data Seed Script (Fresh Environments Only)

The email scrapers for Gotham Comedy Club and Comedy Cellar require a one-time data seed that **cannot run inside a Prisma migration** (the shadow DB used by `migrate dev` would fail if those clubs don't exist). This seed is stored separately:

```
apps/web/prisma/scripts/set_email_scraper_fields.sql
```

**When to run it:** On any **fresh environment** (new Neon database, staging env, disaster-recovery restore) after `prisma migrate deploy` completes and after the clubs data has been seeded. Clubs are populated by normal Prisma migrations — run `prisma migrate deploy` first to ensure the `clubs` rows for "Gotham Comedy Club" and "Comedy Cellar New York" exist before running this script. It is safe to skip on re-deployments where the database already has this data — the script is idempotent.

> **Note:** `prisma migrate deploy` runs the migration `20260308000000_set_email_scraper_fields`, which also attempts these UPDATEs — but silently no-ops if the club rows don't exist yet (it was written this way to be shadow-DB safe). The standalone script is the only path that includes the exception guard to detect missing clubs. Always run the standalone script on fresh environments to confirm the clubs activated correctly.

```bash
cd apps/web
psql $DIRECT_URL -f prisma/scripts/set_email_scraper_fields.sql
```

This sets `scraper = 'gotham_email'` on the Gotham Comedy Club row and `scraper = 'comedy_cellar_email'` on the Comedy Cellar New York row. The script is all-or-nothing: if either club is missing, it raises an exception and rolls back — both clubs must exist before running it. If either club is missing, check that the club names match exactly and that migrations have been fully applied.

> **This step is NOT automated** by the Vercel build command (`prisma migrate deploy && next build`). It must be run manually when provisioning a new environment. Without it, the email scrapers for those two clubs will not activate.

---

## Deploying to Vercel

1. Connect the repo in the Vercel dashboard
2. Set the **Root Directory** to `apps/web`
3. Add all required environment variables in **Settings → Environment Variables** — ensure `NEXT_PUBLIC_*` vars are set as **build-time** variables (not runtime-only)
4. Add `npx prisma migrate deploy &&` before `next build` in the build command if you want migrations to run automatically on deploy
5. Vercel runs the build command automatically on each push to `main`

> **Rollback:** If a deploy is broken, use **Vercel dashboard → Deployments → Promote** to instantly revert to the previous deployment. The Vercel CLI also supports `vercel rollback`. Note that rolling back code does not roll back database schema migrations.

---

## Deploying to Google Cloud Run

The `Dockerfile` is at `apps/web/Dockerfile` and produces a standalone Next.js image that runs on port 3000. The steps below assume you have the [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated.

### 1. Enable Required APIs

```bash
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com
```

### 2. Build and Push the Docker Image

`NEXT_PUBLIC_*` variables are baked into the JavaScript bundle at build time — they must be passed as Docker build arguments, not set at Cloud Run runtime.

```bash
# From the repo root
cd apps/web

# Build — supply NEXT_PUBLIC_* as build args
docker build \
    --build-arg NEXT_PUBLIC_WEBSITE_URL=https://laughtrack.com \
    --build-arg NEXT_PUBLIC_SENTRY_DSN=<your-dsn-or-blank> \
    -t us-docker.pkg.dev/<PROJECT_ID>/laughtrack/web:latest .

# Push to Artifact Registry
docker push us-docker.pkg.dev/<PROJECT_ID>/laughtrack/web:latest
```

Replace `<PROJECT_ID>` with your GCP project ID and `us-docker.pkg.dev` with your Artifact Registry region if different.

> **Sentry DSN:** If you are not using Sentry, omit `--build-arg NEXT_PUBLIC_SENTRY_DSN` or leave the value blank. Sentry is optional.

### 3. Store Secrets in Secret Manager

Use Google Secret Manager to supply runtime environment variables instead of embedding them in the service definition. Create one secret per variable:

```bash
# Example — repeat for each required variable
echo -n "postgres://..." | gcloud secrets create DATABASE_URL --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets create AUTH_SECRET --data-file=-
```

Secrets to create: `DATABASE_URL`, `DIRECT_URL`, `AUTH_SECRET`, `AUTH_URL`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_SECURE`, `EMAIL_FROM`, `BUNNYCDN_CDN_HOST`, `SECRET_KEY`, and any optional secrets (`AUTH_APPLE_ID`, `AUTH_APPLE_SECRET`, `CORS_ALLOWED_ORIGINS`).

Grant the Cloud Run service account access to read each secret:

```bash
gcloud secrets add-iam-policy-binding DATABASE_URL \
    --member="serviceAccount:<SERVICE_ACCOUNT_EMAIL>" \
    --role="roles/secretmanager.secretAccessor"
```

### 4. Deploy the Service

```bash
gcloud run deploy laughtrack-web \
    --image us-docker.pkg.dev/<PROJECT_ID>/laughtrack/web:latest \
    --region us-central1 \
    --platform managed \
    --port 3000 \
    --memory 512Mi \
    --cpu 1 \
    --concurrency 80 \
    --min-instances 1 \
    --set-secrets="DATABASE_URL=DATABASE_URL:latest,\
DIRECT_URL=DIRECT_URL:latest,\
AUTH_SECRET=AUTH_SECRET:latest,\
AUTH_URL=AUTH_URL:latest,\
AUTH_GOOGLE_ID=AUTH_GOOGLE_ID:latest,\
AUTH_GOOGLE_SECRET=AUTH_GOOGLE_SECRET:latest,\
SMTP_HOST=SMTP_HOST:latest,\
SMTP_PORT=SMTP_PORT:latest,\
SMTP_USER=SMTP_USER:latest,\
SMTP_PASSWORD=SMTP_PASSWORD:latest,\
SMTP_SECURE=SMTP_SECURE:latest,\
EMAIL_FROM=EMAIL_FROM:latest,\
BUNNYCDN_CDN_HOST=BUNNYCDN_CDN_HOST:latest,\
SECRET_KEY=SECRET_KEY:latest"
```

**Key service settings:**

| Setting | Recommended | Notes |
|---|---|---|
| `--memory` | `512Mi` | Increase to `1Gi` if you see OOM errors under load |
| `--concurrency` | `80` | Max requests per container instance; Cloud Run default |
| `--min-instances` | `1` | Keeps one instance warm to avoid cold-start latency; set to `0` for pure scale-to-zero (slower first request) |
| `--port` | `3000` | Must match the `EXPOSE 3000` in the Dockerfile |

> **AUTH_URL:** This variable is **required on Cloud Run** (see the Authentication section above). Cloud Run does not auto-detect the canonical URL the way Vercel does. Set it to your service's public URL, e.g. `https://laughtrack.com` or `https://laughtrack-web-<hash>-uc.a.run.app`.

### 5. Connecting to Neon

This project uses `@prisma/adapter-neon` with `@neondatabase/serverless` (WebSocket protocol). Cloud Run containers can reach external services over HTTPS/WSS without any VPC connector. No additional network configuration is required for Neon.

Use the **pooled** Neon connection string for `DATABASE_URL` and the **non-pooled** string for `DIRECT_URL`, exactly as described in the Database section above.

### 6. Run Migrations Before Deploying

Run `prisma migrate deploy` against the live Neon database **before** sending traffic to the new container revision:

```bash
cd apps/web
DATABASE_URL=<pooled-url> DIRECT_URL=<direct-url> npx prisma migrate deploy
```

Then deploy the new image (step 4). Rolling back a Cloud Run revision does **not** roll back database migrations — plan schema changes accordingly.

### 7. Rollback

To revert to the previous revision:

```bash
gcloud run services update-traffic laughtrack-web \
    --to-revisions PREV=100 \
    --region us-central1
```

Or use the Cloud Run console: **Cloud Run → laughtrack-web → Revisions → Route traffic**.

---

## Scraper Secrets (GitHub Actions)

The Python scraper runs via GitHub Actions. Add scraper secrets under **GitHub repo Settings → Secrets and variables → Actions**:

> **Note:** The scraper uses individual `DATABASE_HOST / DATABASE_NAME / DATABASE_USER / DATABASE_PASSWORD / DATABASE_PORT` variables rather than a single connection string (psycopg2 vs Prisma). Both connect to the same Neon database.

| Secret | Description |
|---|---|
| `DATABASE_HOST` | Neon (or Postgres) hostname |
| `DATABASE_NAME` | Database name |
| `DATABASE_USER` | Database username |
| `DATABASE_PASSWORD` | Database password |
| `DATABASE_PORT` | Database port (usually `5432`) |
| `EMAIL_SMTP_SERVER` | SMTP hostname for scraping report emails |
| `EMAIL_SMTP_PORT` | SMTP port |
| `EMAIL_SMTP_USERNAME` | SMTP username |
| `EMAIL_SMTP_PASSWORD` | SMTP password |
| `EMAIL_SMTP_USE_TLS` | `"true"` or `"false"` — for STARTTLS (port 587) |
| `EMAIL_SMTP_USE_SSL` | `"true"` or `"false"` — for SSL (port 465); set to `"false"` when using TLS |
| `EMAIL_FROM_EMAIL` | From address for scraping reports |
| `ALERT_RECIPIENTS` | Comma-separated list of email addresses to receive scraping alerts |
| `MONITORING_WEBHOOK_URL` | (Optional) Webhook URL for monitoring alerts (e.g. Slack incoming webhook) |
| `TICKETMASTER_API_KEY` | (Optional) Ticketmaster API key |
| `SONGKICK_API_KEY` | (Optional) Songkick API key |
| `BANDSINTOWN_APP_ID` | (Optional) Bandsintown app ID |
| `EVENTBRITE_PRIVATE_TOKEN` | (Optional) Eventbrite private token |
| `SEATENGINE_AUTH_TOKEN` | (Optional) SeatEngine auth token — the scraper has a built-in default but production deployments should set this explicitly |
| `SLACK_WEBHOOK_URL` | (Optional) Slack webhook for scraping alerts |
| `MAX_CONCURRENT_CLUBS` | (Optional) Max clubs scraped simultaneously (default: `5`) |

These secrets are consumed by the scraper application and should be added to any GitHub Actions workflow that runs the scraper in production.

---

## Quick Reference: Required vs Optional

### Required for any deployment

- `DATABASE_URL`
- `DIRECT_URL`
- `AUTH_SECRET` (or legacy alias `NEXTAUTH_SECRET`)
- `AUTH_URL` (required on Cloud Run; optional on Vercel)
- `AUTH_GOOGLE_ID`
- `AUTH_GOOGLE_SECRET`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_SECURE`, `EMAIL_FROM`
- `BUNNYCDN_CDN_HOST`
- `SECRET_KEY`
- `NEXT_PUBLIC_WEBSITE_URL` **(build-time)**

### Optional

- `AUTH_APPLE_ID`, `AUTH_APPLE_SECRET` — enables Apple Sign In (both required together)
- `CORS_ALLOWED_ORIGINS` — defaults to `NEXT_PUBLIC_WEBSITE_URL`
- `NEXT_PUBLIC_SENTRY_DSN` — enables Sentry error tracking **(build-time)**
- `DIRECTORY_PATH` — local file storage path (not needed on Vercel/Cloud Run)
- `K_REVISION` — auto-set by Cloud Run, do not set manually

---

## Uptime Monitoring & Incident Response

Production uptime is monitored by [UptimeRobot](https://uptimerobot.com). Pages route to the **`#laughtrack` channel in Discord** (same destination as Sentry alerts) via UptimeRobot's native Discord webhook alert contact.

> **Why not Better Stack:** Better Stack has no native Discord integration. The recommended workaround uses its Slack integration, but Better Stack's Slack OAuth requires a real (paid) Slack workspace to install the app — we don't have one and don't want to pay for one just for paging. UptimeRobot's Discord support is first-class and works on its free tier.

### What gets probed

| Monitor | URL | Why |
|---|---|---|
| Homepage canary | `https://laugh-track.com/` | Full SSR path — catches DB / Prisma / NextAuth / CDN failures that a thin liveness check would miss |
| Liveness probe | `https://laugh-track.com/api/health` | Cheap 200 OK from `apps/web/app/api/health/route.ts`. No DB dependency, so it stays green during transient DB blips while the homepage tells you whether real traffic is affected |

The homepage is the leading signal (deep canary). The `/api/health` endpoint is a corroborating signal — if both fail, the app is hard-down; if only the homepage fails, the outage is in the data layer or middleware.

### "Down" criteria

A monitor is considered **down** when **any** of the following holds for **2 consecutive checks** (≥ 10 minutes of failure at the UptimeRobot free-tier 5-minute interval; paid plans probe every 30–60s and bring detection time down accordingly):

- HTTP status ≥ 500, or
- Request times out (no response within **10 seconds** for `/api/health`, **15 seconds** for `/`), or
- TLS handshake fails

Two consecutive failures (rather than one) suppresses single-region network blips. UptimeRobot's multi-region probes (US, EU, Asia) with majority-rules confirmation further reduce false positives.

A monitor is considered **recovered** after **2 consecutive successful checks**.

### Paging destination

- **Primary:** Discord `#laughtrack` channel via UptimeRobot's native Discord alert contact (the Discord channel's incoming webhook URL is pasted directly into UptimeRobot as a Webhook-type alert contact; UptimeRobot's Discord integration emits a Discord-formatted payload, so no Slack-compatibility trick is required).
- **Escalation:** Email to `gioematt@gmail.com` as a second alert contact on each monitor; UptimeRobot will email immediately on every state change.

Both contacts fire on `down`; both also fire on `recovered`.

### Who responds

Matt Gioe (`gioematt@gmail.com`) is the sole on-call. There is no rotation. If unreachable, the site stays down — flag this in the post-incident retro and add an escalation contact.

### Incident response steps

When a page fires:

1. **Acknowledge** in UptimeRobot (mobile app or dashboard) to stop further pages while you investigate.
2. **Reproduce** — open `https://laugh-track.com/` and `https://laugh-track.com/api/health` from your browser. Note which is failing.
3. **Triage by failure pattern:**
   - **Both endpoints down** → app is hard-down. Check the [Vercel dashboard](https://vercel.com/dashboard) for the latest deployment status. If a recent deploy looks suspect, **Vercel → Deployments → Promote** the previous successful deployment to roll back.
   - **Only `/` down, `/api/health` up** → SSR / DB path is broken. Check:
     - [Neon console](https://console.neon.tech) — is the compute endpoint suspended or out of CPU credits?
     - [Sentry](https://sentry.io) — any new spike of errors on the homepage route?
     - Vercel logs for the most recent deployment.
   - **Only `/api/health` down, `/` up** → unlikely (homepage covers the same Node runtime). Treat as Vercel infrastructure flap; wait 5 minutes before deeper investigation.
4. **Communicate** — drop a note in `#laughtrack` Discord describing what you're seeing, even if you don't have a fix yet.
5. **Resolve and close** the incident in UptimeRobot once both monitors are green for ≥ 5 minutes.
6. **Post-incident** — file a tusk task (`/create-task`) capturing root cause, time to detect, time to resolve, and any follow-up work (e.g. add a new alert, fix a brittle code path).

### One-time UptimeRobot setup

Performed once; record the resulting monitor IDs in 1Password / a secure note.

1. Sign up for [UptimeRobot](https://uptimerobot.com) (free tier covers 50 monitors at 5-minute intervals; paid Solo tier adds 30s–60s intervals).
2. Create a Discord incoming webhook in the `#laughtrack` channel (Discord → Channel Settings → Integrations → Webhooks → New Webhook). Copy the webhook URL. Do **not** append `/slack` — UptimeRobot posts in Discord's native format.
3. In UptimeRobot: **My Settings → Add Alert Contact → Type: Webhook**. Paste the Discord webhook URL from step 2. Enable **Send as JSON (application/json)** and use a Discord-compatible POST body that interpolates UptimeRobot's variables, for example:
   ```json
   {
     "content": "🚨 **\*monitorFriendlyName\*** is **\*alertTypeFriendlyName\***",
     "embeds": [{
       "title": "\*monitorFriendlyName\*",
       "url": "\*monitorURL\*",
       "description": "\*alertDetails\*",
       "color": 15158332
     }]
   }
   ```
4. Add a second alert contact: **Type: E-mail**, address `gioematt@gmail.com`, for escalation redundancy.
5. **Monitors → New Monitor** twice — once per URL above. For each:
   - **Monitor Type:** HTTP(s)
   - **URL:** `https://laugh-track.com/` and `https://laugh-track.com/api/health`
   - **Monitoring Interval:** 5 minutes (free tier) or 1 minute (paid tier if upgraded)
   - **Timeout:** 15s for `/`, 10s for `/api/health`
   - **Alert Contacts:** select both the Discord webhook and the email contact created above
   - **HTTP Status Codes:** alert on anything that is not `200`
6. Trigger a test failure: pause one monitor manually (Monitors → ⏸) and confirm Discord receives the alert in `#laughtrack`. Resume the monitor.
7. Document the monitor IDs in the team notes so they can be referenced from future runbooks.
