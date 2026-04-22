---
name: seatengine-audit
description: "Bulk health audit of all visible SeatEngine-scraped clubs. Usage: /seatengine-audit"
allowed-tools: Bash
---

# SeatEngine Audit

Bulk health audit of all visible SeatEngine-scraped clubs. Checks every club with
`scraper='seatengine'` against the SeatEngine API and categorizes them as healthy,
empty, or dead.

## Usage

```
/seatengine-audit
```

No arguments required.

## Step 1: Run the Audit

```bash
cd apps/scraper && make seatengine-audit
```

The command checks all visible clubs with `scraper='seatengine'`, hits the SeatEngine
API for each, and prints a categorized report. Exits with:
- **0** = all venues healthy
- **2** = at least one venue is dead or empty

## Step 2: Interpret Results

The report groups venues into:

| Category | Meaning | Action |
|----------|---------|--------|
| **Healthy** | API responds with 1+ shows | No action needed |
| **Empty** | API responds but 0 shows | May be genuinely empty or moved platforms |
| **Dead** | API returns 404 | Venue no longer on SeatEngine |
| **Errors** | API call failed or no seatengine_id | Investigate individually |

## Step 3: Triage Dead and Empty Venues

For **dead** venues (404):
- These are strong candidates for `/hide-club <id>` if the venue is confirmed closed
- Or `/adopt-scraper <name>` if the venue may have moved to a different platform

For **empty** venues:
- A venue with 0 shows is not necessarily broken — it may be genuinely between shows
- Prioritize investigating venues that have been empty for 7+ days (cross-reference
  with triage tasks in the backlog)
- Use `/seatengine-check <se_id>` for individual follow-up

For **errors**:
- Check if the `seatengine_id` is correct in the DB
- May indicate auth token expiration — run `/fetch-seatengine-token` to refresh

## Step 4: Report Summary

After the audit completes, present:

```
SeatEngine Audit Summary
━━━━━━━━━━━━━━━━━━━━━━━━
Total:    <N> clubs
Healthy:  <N> (<percentage>%)
Empty:    <N> (<percentage>%)
Dead:     <N>
Errors:   <N>

Recommended actions:
- <list of specific actions based on findings>
```

If the user wants to act on findings, suggest:
- `/hide-club <id>` for confirmed dead venues
- `/adopt-scraper <name>` for venues that may have moved platforms
- `/create-task` to batch-create triage tasks for empty venues
