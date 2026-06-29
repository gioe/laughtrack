# TASK-3518 — Enabled scraping_sources that never run in the nightly

**Date:** 2026-06-29
**Origin:** TASK-3511 retro — Liberty Funny Bone (11431) had an enabled etix source but
0 `scraper_run_clubs` rows, yet produced 113 shows when invoked manually. Hypothesis: the
nightly orchestrator silently skips some enabled sources.

## Verdict

**No systemic orchestrator gap.** "0 `scraper_run_clubs` rows" is a **misleading coverage
signal** — it does not mean "never scraped." It conflates three benign cases. The genuine
coverage-gap query returns **empty**.

## Criterion 11560 — enumerate never-run enabled sources

Enabled sources whose `club_id` has 0 lifetime `scraper_run_clubs` rows: **19 total**.

| scraper_key | count | why 0 per-club run rows |
|-------------|------:|--------------------------|
| eventbrite | 10 | 8 are venue clubs fed by an **organizer** feed (the run is attributed to the organizer club, not the downstream venue) + 2 are `visible=false` |
| live_nation | 8 | covered by the **`ticketmaster_national`** bulk job (`shows.last_scraped_by='ticketmaster_national'`); the national run is attributed to the national feed, not per-club |
| json_ld | 1 | `Let's Comedy Venues` (410), `visible=false` |

Every one of the 19 **already has shows** (1–42 each), with fresh `last_show_scrape` (mostly
2026-06-26/29 for the covered ones). They are actively covered; they just never get a
*direct per-club* `scraper_run_clubs` row because a parent scraper does the work.

## Criterion 11561 — root cause for Liberty Funny Bone (11431)

**Fresh-onboard timing, not an orchestrator skip.**

- Liberty's etix source was added **2026-06-26 22:33:27 UTC**.
- That day's full nightly (`run_type='scraper'`, 1490 clubs) ran at **2026-06-26 22:22:33
  UTC** — **~11 minutes before** the source existed, so `get_all_clubs()` never saw it.
- The nightly is **not strictly daily**: full runs (>100 clubs) landed on Jun 26, 24, 22,
  21, 16, 15, 14… There was **no full run on Jun 27, 28, or 29**, so Liberty has had **no
  run opportunity** since onboarding.
- Liberty is `visible=true`, `status='active'`, with an enabled source — it satisfies the
  nightly's `GET_ALL_CLUBS` filter (`WHERE c.visible = TRUE AND c.status = 'active'`), so the
  **next full nightly will pick it up**. The TASK-3511 manual `scrape_shows --club-id 11431`
  just ran it early (and wrote its first `scraper_run_clubs` row).

## Criterion 11562 — systemic gap? (no) — documented

The 19 break down with **no uncovered venue**:

1. **Aggregate-covered (16)** — eventbrite organizer venue clubs + `ticketmaster_national`
   venue clubs. 0 per-club run rows is **expected**: the parent scraper attributes the run to
   the parent entity (organizer club / national feed). These have fresh shows. Working as
   designed.
2. **`visible=false` (3)** — Busboys and Poets TAKOMA (2293), 104 E 5th St (2313), Let's
   Comedy Venues (410). `GET_ALL_CLUBS` intentionally filters `visible = TRUE`, so hidden
   clubs are **excluded from `--all` by design** (we don't scrape clubs users can't see).
   Two still receive shows via organizer attribution; 410 is a stale json_ld producer-ish
   entry (last scrape 2026-06-01) but is hidden on purpose.
3. **Liberty (1)** — fresh-onboard timing (above); already recovered.

**The genuine coverage-gap query returns empty:**

```sql
SELECT c.id FROM clubs c
JOIN scraping_sources ss ON ss.club_id=c.id AND ss.enabled=true
WHERE c.visible=true AND c.status='active'
  AND NOT EXISTS (SELECT 1 FROM scraper_run_clubs r WHERE r.club_id=c.id)
  AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id=c.id);
-- → 0 rows
```

So there is no Liberty-type venue (visible, enabled source, 0 shows, never run) left to
recover. **No fix required; task closed.**

## Note for the audit-metric refinement (TASK-3520)

"0 `scraper_run_clubs` rows" should **not** be used as a never-scraped / coverage-gap signal.
The correct gap query is the one above — *visible + active + enabled source + 0 shows +
0 run rows* — which excludes aggregate-covered venue clubs (organizer/national), hidden
clubs, and just-onboarded clubs awaiting their first nightly. Same class of
metric-misinterpretation as the `stale_30d` finding folded into TASK-3520.
