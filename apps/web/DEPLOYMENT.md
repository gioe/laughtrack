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
| `DATABASE_URL` | Yes | Pooled connection URL used by Prisma at runtime. For Neon: use the **pooled** connection string (includes `?pgbouncer=true`). |
| `DIRECT_URL` | Yes | **Non-pooled** Neon connection URL. Must be the direct endpoint — not the pooled one. Required for `prisma migrate deploy` to work. |

> **Important:** `DIRECT_URL` must be the **non-pooled** Neon URL (the one that does **not** include `?pgbouncer=true`). Prisma uses this URL when running migrations. If you point it at the pooled endpoint, `prisma migrate deploy` will fail with a transaction error.

In the Neon dashboard, find both URLs under **Connection Details**:
- Pooled → `DATABASE_URL`
- Direct → `DIRECT_URL`

### Authentication (Required)

| Variable | Required | Description |
|---|---|---|
| `NEXTAUTH_SECRET` | Yes | Random secret used to sign session tokens. Generate with: `openssl rand -base64 32` |
| `AUTH_URL` | Yes | Canonical URL of the app (e.g. `https://laughtrack.com`). Required on Cloud Run where the host cannot be inferred. Use `http://localhost:3000` locally. |
| `AUTH_GOOGLE_ID` | Yes | Google OAuth client ID. Create credentials at [console.cloud.google.com](https://console.cloud.google.com). |
| `AUTH_GOOGLE_SECRET` | Yes | Google OAuth client secret. |
| `AUTH_APPLE_ID` | No | Apple Sign In service ID. Added post-TASK-91. See setup instructions below. |
| `AUTH_APPLE_SECRET` | No | Apple Sign In private key (.p8 file contents). Added post-TASK-91. See setup instructions below. |

#### Generating NEXTAUTH_SECRET

```bash
openssl rand -base64 32
```

#### Apple Sign In Setup (AUTH_APPLE_ID / AUTH_APPLE_SECRET)

Apple OAuth credentials were added in TASK-91 and are optional — the app works without them (Google and magic-link email sign-in remain available).

To enable Apple Sign In:

1. Go to [developer.apple.com](https://developer.apple.com) → Certificates, Identifiers & Profiles
2. Create a **Services ID** (this becomes `AUTH_APPLE_ID`)
3. Create a **Key** with Sign In with Apple enabled, download the `.p8` file
4. `AUTH_APPLE_SECRET` must be the full contents of the `.p8` file with newlines replaced by literal `\n`:
   ```
   -----BEGIN PRIVATE KEY-----\nMIGT...\n-----END PRIVATE KEY-----
   ```
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

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_WEBSITE_URL` | Yes | Canonical URL of the site (e.g. `https://laughtrack.com`). Used for absolute URLs and OG meta tags. |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated list of allowed CORS origins. Defaults to `NEXT_PUBLIC_WEBSITE_URL` if not set. |

### Error Tracking (Optional)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_SENTRY_DSN` | No | Sentry DSN from your project's Client Keys page. Leave empty in development. |

### Cloud Run (Auto-Set)

| Variable | Required | Description |
|---|---|---|
| `K_REVISION` | Auto | Set automatically by Google Cloud Run. Used to detect cloud environment. Do **not** set this manually. |

---

## Running Migrations

Always use `prisma migrate deploy` (not `prisma migrate dev`) in production:

```bash
cd apps/web
DATABASE_URL="<pooled-url>" DIRECT_URL="<direct-url>" npx prisma migrate deploy
```

`DIRECT_URL` must be set to the **non-pooled** Neon endpoint. The pooled endpoint uses PgBouncer in transaction mode which blocks the advisory locks that migration tracking requires.

---

## Deploying to Vercel

1. Connect the repo in the Vercel dashboard
2. Set the **Root Directory** to `apps/web`
3. Add all required environment variables in **Settings → Environment Variables**
4. Vercel runs `npm run build` automatically on each push to `main`

---

## Scraper Secrets (GitHub Actions)

The Python scraper runs via GitHub Actions. Add scraper secrets under **GitHub repo Settings → Secrets and variables → Actions**:

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
| `EMAIL_SMTP_USE_TLS` | `"true"` or `"false"` |
| `EMAIL_FROM_EMAIL` | From address for scraping reports |
| `EMAIL_SCRAPING_REPORT_RECIPIENTS` | Comma-separated list of report recipients |
| `TICKETMASTER_API_KEY` | (Optional) Ticketmaster API key |
| `SONGKICK_API_KEY` | (Optional) Songkick API key |
| `BANDSINTOWN_APP_ID` | (Optional) Bandsintown app ID |
| `EVENTBRITE_PRIVATE_TOKEN` | (Optional) Eventbrite private token |
| `SLACK_WEBHOOK_URL` | (Optional) Slack webhook for scraping alerts |
| `MAX_CONCURRENT_CLUBS` | (Optional) Max clubs scraped simultaneously (default: `5`) |

These secrets are injected into the scraper GitHub Actions workflow at runtime and are never stored in the repository.

---

## Quick Reference: Required vs Optional

### Required for any deployment

- `DATABASE_URL`
- `DIRECT_URL`
- `NEXTAUTH_SECRET`
- `AUTH_URL`
- `AUTH_GOOGLE_ID`
- `AUTH_GOOGLE_SECRET`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_SECURE`, `EMAIL_FROM`
- `BUNNYCDN_CDN_HOST`
- `SECRET_KEY`
- `NEXT_PUBLIC_WEBSITE_URL`

### Optional

- `AUTH_APPLE_ID`, `AUTH_APPLE_SECRET` — enables Apple Sign In
- `CORS_ALLOWED_ORIGINS` — defaults to `NEXT_PUBLIC_WEBSITE_URL`
- `NEXT_PUBLIC_SENTRY_DSN` — enables Sentry error tracking
- `K_REVISION` — auto-set by Cloud Run, do not set manually
