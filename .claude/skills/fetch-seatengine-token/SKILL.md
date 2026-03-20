---
name: fetch-seatengine-token
description: Refresh SEATENGINE_AUTH_TOKEN from SeatEngine's public cart bundle and write it to apps/scraper/.env. Usage: /fetch-seatengine-token [--gh-secret] [--venue-url <url>]
allowed-tools: Bash
---

# Fetch SeatEngine Token Skill

Extracts the public `SEATENGINE_AUTH_TOKEN` from SeatEngine's React cart bundle
and updates `apps/scraper/.env`. The token is a UUID embedded in plaintext in every
SeatEngine venue's frontend — it is public and shared across all venues.

## Background

SeatEngine venue pages have two layers:
- **Server-rendered events list** — no API calls, no token visible in network traffic
- **React cart widget** (`cdn-new.seatengine.com/cart-*.js`) — loaded client-side, contains `APP_AUTH_TOKEN` in plaintext

The token is sent as `x-auth-token` to `services.seatengine.com/api/v1/venues/*/shows`.

## Arguments

Parse `ARGUMENTS`:
- `--gh-secret` → also set the token in GitHub Actions secrets via `gh secret set`
- `--venue-url <url>` → override the SeatEngine venue URL to fetch from
- _(no args)_ → refresh token from default venue, update `.env` only

## Steps

1. Run the extraction script, passing through any arguments:

```bash
bash apps/scraper/scripts/fetch_seatengine_token.sh ARGUMENTS
```

2. Print the result. If the script exits non-zero, surface the error output to the user.

3. If `--gh-secret` was passed, confirm that both `.env` and GitHub secrets were updated.
   If `--gh-secret` was not passed, remind the user:
   > To also update GitHub Actions secrets, run: `/fetch-seatengine-token --gh-secret`
