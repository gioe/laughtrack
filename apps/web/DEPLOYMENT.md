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
| `NEXTAUTH_SECRET` | Yes | Random secret used to sign session tokens. Generate with: `openssl rand -base64 32`. **Rotating this secret invalidates all active user sessions immediately.** |
| `AUTH_URL` | Yes (Cloud Run) / No (Vercel) | Canonical URL of the app (e.g. `https://laughtrack.com`). Required on Cloud Run where the host cannot be inferred from the request. On Vercel, NextAuth v5 auto-detects the URL from `VERCEL_URL`. Use `http://localhost:3000` locally. |
| `AUTH_GOOGLE_ID` | Yes | Google OAuth client ID. Create credentials at [console.cloud.google.com](https://console.cloud.google.com). |
| `AUTH_GOOGLE_SECRET` | Yes | Google OAuth client secret. |
| `AUTH_APPLE_ID` | No | Apple Sign In service ID. Added post-TASK-91. See setup instructions below. Both `AUTH_APPLE_ID` and `AUTH_APPLE_SECRET` must be set together — the Apple provider is always registered in `auth.ts` and will fail at sign-in if either var is missing. |
| `AUTH_APPLE_SECRET` | No | Apple Sign In private key (.p8 file contents). Added post-TASK-91. |

#### Generating NEXTAUTH_SECRET

```bash
openssl rand -base64 32
```

> **Operational note:** `NEXTAUTH_SECRET` and `SECRET_KEY` must be identical across all running instances (e.g. multiple Cloud Run revisions or Vercel preview deployments sharing the same Neon DB). Changing `NEXTAUTH_SECRET` in production will immediately log out all users.

#### Apple Sign In Setup (AUTH_APPLE_ID / AUTH_APPLE_SECRET)

Apple OAuth credentials were added in TASK-91 and are optional — the app works without them (Google and magic-link email sign-in remain available). However, if either variable is absent, the Apple sign-in button will appear but fail.

To enable Apple Sign In:

1. Go to [developer.apple.com](https://developer.apple.com) → Certificates, Identifiers & Profiles
2. Create a **Services ID** (this becomes `AUTH_APPLE_ID`)
3. Create a **Key** with Sign In with Apple enabled, download the `.p8` file
4. `AUTH_APPLE_SECRET` must be the full contents of the `.p8` file with newlines replaced by literal `\n`:
   ```
   -----BEGIN PRIVATE KEY-----\nMIGT...\n-----END PRIVATE KEY-----
   ```
   > **Warning:** Some hosting provider UIs (including certain Vercel flows) will double-escape the backslash, breaking Apple Sign In silently. Verify the stored value contains single `\n` sequences, not `\\n`. Test Apple auth end-to-end in staging before relying on it in production.
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

**When to run it:** On any **fresh environment** (new Neon database, staging env, disaster-recovery restore) after `prisma migrate deploy` completes and after the clubs data has been seeded. It is safe to skip on re-deployments where the database already has this data — the script is idempotent.

```bash
cd apps/web
psql $DIRECT_URL -f prisma/scripts/set_email_scraper_fields.sql
```

This sets `scraper = 'gotham_email'` on the Gotham Comedy Club row and `scraper = 'comedy_cellar_email'` on the Comedy Cellar New York row. If either club is missing, the script raises an exception rather than silently skipping — check that club names match exactly.

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
- `NEXTAUTH_SECRET`
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
