---
name: check-seatengine-token
description: Verify that the SEATENGINE_AUTH_TOKEN in apps/scraper/.env is still accepted by the SeatEngine API. Usage: /check-seatengine-token
---

# Check SeatEngine Token Skill

Verifies the current `SEATENGINE_AUTH_TOKEN` in `apps/scraper/.env` is still valid
by testing it against the SeatEngine v1 API.

## Background

The SeatEngine API requires an `x-auth-token` header. The token is a static UUID
that does not rotate frequently. This skill confirms it still works.

## Steps

1. Run the check script:

```bash
bash apps/scraper/scripts/check_seatengine_token.sh
```

2. Report the result:

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| **0** | Token is valid | No action needed. |
| **1** | Token is expired, missing, or API unreachable | The token needs manual replacement. Check SeatEngine network traffic via Playwright to capture a fresh `x-auth-token` from any `services.seatengine.com` API call. |
