---
name: analyze-scraping-data
description: Audit production scraping outputs to find broken or degraded scrapers — runs SQL across clubs/sources/shows/tickets/lineups and classifies findings as critical / worth-investigating / healthy
allowed-tools: Bash, Read, Write
---

# Analyze Scraping Data

End-to-end health check on what the LaughTrack scrapers are actually producing in prod. Reveals scrapers that are:

- producing **0 shows** despite having enabled sources (likely fully broken),
- producing shows with **no tickets** (silently invisible — the UI gates on `tickets.length > 0`),
- producing shows with **no lineup items** (search/notification-quality gap),
- producing tickets with **NULL prices** at high rates (price-extraction regression),
- producing shows with **midnight times** at high rates (time-parsing regression),
- haven't been **touched recently** (cron / config drift), or
- have **all-sold-out** ticket sets (often a soft-fail from the scraper marking unavailable inventory as `sold_out=true` instead of dropping it).

Run this whenever a scraper PR lands, after a nightly run, when investigating "is anything broken right now?", or as a periodic backlog generator.

## Step 1: Run the audit script

The audit lives at `apps/scraper/scripts/core/audit_scraping_data.py`. It executes ~15 read-only SQL queries against the production DB via the standard `laughtrack.adapters.db.get_connection`. Output is plain-text tables.

```bash
cd apps/scraper && .venv/bin/python scripts/core/audit_scraping_data.py
```

Capture the output — it's typically 200-500 lines, organized into nine sections:

1. Inventory (clubs / sources / shows)
2. Per-scraper productivity (last 7 days)
3. Zero-output scrapers (enabled sources with 0 upcoming shows) — **plus a "Dead sources classified by run health" sub-query** that buckets each into `never_run` / `broken_bot_block` / `broken_error` / `dormant_recently_productive` / `dormant_dark` (TASK-3520). The raw per-platform `dead_sources` count over-reports; read the classification instead.
4. Stale scrapes (never_scraped / stale_2d / stale_7d / stale_30d) — **plus a "stale_30d clubs classified by run health" sub-query.** `stale_30d` on its own is NOT a "dead scraper" signal: `shows.last_scraped_date` only refreshes when a show is written, so a venue whose nightly succeeds with 0 events stays "stale" forever (conventions #293/#294).
5. Show data quality (missing fields, no tickets, no lineup)
6. Ticket data quality (NULL price, sold-out, etc.)
7. Anomalous dates (midnight, far-future, far-past)
8. Chain coverage
9. Lineup health

## Step 2: Classify findings against thresholds

Walk the output top-to-bottom. Use these thresholds — they're calibrated to the current data shape, where ~25k upcoming shows are produced by ~80 distinct scraper keys across 25 platforms.

### 🔴 Critical (likely broken — file a task)

| Signal | Threshold |
|---|---|
| Per-scraper `pct_null_price` (Section 6) | **≥ 50%** with ≥ 50 tickets |
| Per-scraper `pct_empty` lineup (Section 9) | **≥ 80%** with ≥ 50 upcoming shows |
| `broken_bot_block` / `broken_error` clubs in the run-health classification (Sections 3 & 4) | **≥ 1** — most recent run actually failed or was bot-blocked. This is the real "scraper is broken" signal (replaces the raw `dead_sources` / `stale_30d` heuristics, which over-report). |
| `never_run` clubs in the run-health classification (Sections 3 & 4) | **≥ 1** — visible+active club with an enabled source and 0 `scraper_run_clubs` rows AND 0 shows = genuine coverage gap. (NB: aggregate-covered venue clubs — eventbrite organizer / `ticketmaster_national` — are NOT here; they have shows. TASK-3518.) |
| `shows_per_source` for a platform (Section 2) | **< 10** when global median is ~70 |
| `shows_without_tickets` for any scraper (Section 5) | **any non-zero** — these shows are invisible in the UI per the "tickets are access records" invariant |

### 🟡 Worth investigating (degraded, not broken)

| Signal | Threshold |
|---|---|
| `pct_null_price` per scraper | 10-50% |
| `pct_empty` lineup per scraper | 30-80% |
| `pct_midnight` per scraper (Section 7) | ≥ 50% with ≥ 20 upcoming shows — possible time-parsing bug, but some platforms (RSVP-only / day-card events) legitimately don't carry showtime. The query buckets by **club-local** time (`date AT TIME ZONE club.timezone`), so an evening showtime no longer masquerades as midnight (see the gotcha below) |
| `all_sold_out_shows` for any scraper | ≥ 10 — could be real, or scraper miscoding unavailable inventory |
| `dormant_dark` clubs in the run-health classification | many — real venues with no current programming on their source; not broken, but a long-dark cluster on one platform is worth a spot-check |
| `stale_7d` for a platform | ≥ 1 — but confirm via the run-health classification before treating as broken (see Sections 3 & 4) |
| Disabled `scraping_sources` rows still present | Any — should be deleted not disabled (`check_scraping_source_invariants.py`) |
| Chain with `active_visible` clubs but `upcoming_shows` < 10 × clubs | Possible scraper outage at a chain level |

### 🟢 Healthy signals to confirm

- Total upcoming-show count matches recent baseline (last known: ~26k).
- All major platforms (`seatengine`, `eventbrite`, `ticketmaster`, `custom`) have `enabled_sources > 0` and **0 `never_run` / `broken_*` clubs in the run-health classification** (a high `dormant_*` count is healthy, not a problem).
- No shows with `missing_url` or `no_attribution` (Section 5).
- No shows with `very_old` or `very_far_future` dates (Section 7).
- `<null>` `last_scraped_by` rows in Section 2 are all in the past (i.e., `upcoming_touched = 0`).

## Step 3: Cross-reference before flagging

Before declaring something broken, check obvious confounders:

- **Open backlog**: `tusk task-list --search "<scraper-key>"` — there may already be an in-flight task. The current branch list (e.g. `TASK-2098-live-nation-price-extraction`, `TASK-2090-fix-seatengine-classic-price-extraction`) is a fast smoke check.
- **Disabled by design**: `tusk conventions search <platform>` — some venues are intentionally on a degraded scraper.
- **Recent migrations**: `git log --oneline -- apps/web/prisma/migrations | head -20` — a recent disposition migration may have just dropped sources/shows.
- **Single-club scrapers**: a venue-specific scraper (e.g. `comedy_mothership`, `io_theater`) producing 0 shows is more suspicious than `seatengine` having 1 dead source out of 137.
- **GHA vs local**: per the `regression_verify_gha` feedback, a clean local scrape doesn't disprove a nightly regression — WAFs treat GHA IPs differently.

## Step 4: Write the report

Output a structured summary in this format:

```
## Scraping audit — <YYYY-MM-DD>

**Inventory:** <X> upcoming shows across <Y> clubs / <Z> enabled sources.

### 🔴 Critical
- <scraper>: <metric> (<value>) — <one-line interpretation>. Suggested action: <verify with X / file task>.
- ...

### 🟡 Worth investigating
- ...

### 🟢 Healthy
- <sentence per major platform>
```

Keep it skimmable. Include the raw number every time so the user can verify against the audit output without re-running.

## Step 5: Optional follow-ups

Offer (don't auto-execute):

- **File tasks** for each 🔴 finding via `/create-task` (it dedupes against the existing backlog — required per the `dupe_check_before_followup` feedback).
- **Re-run after a fix** to confirm the metric moved.
- **Add to `/loop`** if the user wants a periodic check (e.g. weekly cadence).

## Notes & gotchas

- The script is **read-only**. Safe to run repeatedly.
- It uses `last_scraped_by` for attribution; some legacy shows have `<null>` here. Section 2 surfaces this — don't conflate with "no recent scrape".
- "Shows with no tickets" is a meaningful invariant violation per `feedback_tickets_are_access_records`: every show should emit ≥ 1 ticket, even free / RSVP-only events. The UI hides ticketless shows.
- Zero-priced tickets are NOT a violation by themselves — they're how free events are represented. Only escalate if combined with other red flags (e.g., a scraper with both 100% zero-price *and* 100% sold-out).
- The `midnight_upcoming` count includes legitimate all-day / open-mic / RSVP-only events. Use the per-scraper rate (`pct_midnight`) rather than the absolute count.
- **Midnight is measured in club-local time, not UTC** (TASK-3516). `shows.date` is a UTC `timestamptz`; a bare `date::time` reads the time-of-day in UTC, which mislabels every evening show west of UTC as "midnight" (7pm Central / 6pm Mountain / 5pm Pacific / 8pm-EDT all map to 00:00 UTC). The Section 7 queries convert via `date AT TIME ZONE club.timezone` first, so only true local-midnight shows count. If you hand-roll a midnight check, do the same — otherwise zanies, esthers_follies, fareharbor (all confirmed correct) and any other non-UTC venue will trip a false time-parse alarm.
- This skill does NOT trigger scrapes. To re-run a scraper for one club, use `make -C apps/scraper club ID=<n>` (per `feedback_use_make_commands`).
