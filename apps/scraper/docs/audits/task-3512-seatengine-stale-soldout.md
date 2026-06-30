# TASK-3512 — SeatEngine: 5 stale-30d sources + 103 all-sold-out shows

**Date:** 2026-06-29
**Source:** 2026-06-29 scraping-data audit (`audit_scraping_data.py` sections 4 & 6).
**Verdict:** Both signals are **benign** — the SeatEngine scraper is healthy. No code or
config repair was required. Disposition: confirm-and-leave.

SeatEngine is a core high-yield platform (133 enabled sources, ~11.4k upcoming shows).
Two audit signals were flagged; each was reproduced and run to ground.

---

## Signal 1 — 5 stale-30d clubs (criterion 11551)

The audit's `stale_30d` counter = clubs whose `MAX(shows.last_scraped_date)` is older than
30 days. The 5 clubs (excluding the 3 never-scraped NULL ones, which are a separate bucket
already triaged under TASK-3511/TASK-3518):

| club_id | venue | last show date | SeatEngine venue | nightly runs | diagnosis |
|--------:|-------|----------------|------------------|-------------:|-----------|
| 60 | Cherokee Comedy Zone (Cherokee, NC) | 2025-07-07 | classic (site embed) | 27, all success | dormant — site still embeds SeatEngine, calendar empty |
| 89 | Beaches Comedy Club (Panama City Beach, FL) | 2025-07-07 | venue 543 | 27, all success | dormant — site still embeds SeatEngine, 0 events |
| 636 | Wicked Funny Comedy Club Danvers (Danvers, MA) | 2026-04-11 | venue 641 | 27, all success | dormant — venue resolves, 0 events |
| 833 | Portland Comedy Club (Portland, OR) | 2026-05-22 | venue 260 | 27, all success | dormant — venue resolves, 0 events (public site currently unreachable) |
| 855 | Laugh Tonight Comedy (Jersey City, NJ) | 2026-05-27 | venue 424 | 27, all success | dormant — venue resolves, 0 events |

**Diagnosis: all 5 sources are healthy; the venues are dark, not the scrapers.**

Evidence:
- Each was live-probed (`scrape_shows --club-id <id>`). Every one returned **HTTP 200**,
  the SeatEngine venue **resolved** (`services.seatengine.com/api/v1/venues/<id>`), produced
  **0 events**, and showed **no bot-block** (`no events found for venue <id>` / classic feed
  empty).
- Production run history confirms (GHA, not just local — per the regression-verify-GHA rule):
  each club has **27 runs, last 2026-06-29, all `success=true`, `bot_block=false`, and
  `max(num_shows)=0`** across the entire window. The nightly runs them every night and they
  have simply never had an event in that window.
- The two year-stale venues (Cherokee 60, Beaches 89) **still embed SeatEngine** on their own
  sites (9–11 hits for `seatengine` in the page HTML) — they have **not** moved platforms, so
  there is no new source to adopt. Their SeatEngine calendars are just empty.

**Why `last_scraped_date` looks stale even though the scraper runs nightly:**
`last_scraped_date` is stamped on `shows` rows. A club with **0 current shows** never gets a
fresh `last_scraped_date` — the `MAX()` stays pinned to whenever the venue last had a show.
So `stale_30d` here is a **symptom of venue dormancy, not a dead scraper**. The audit metric
conflates "dormant-but-running" with "broken." (See the retro follow-up to refine the audit
to key off `scraper_run_clubs` success/error instead of show `last_scraped_date`.)

**Disposition:** real venues, healthy sources, dormant calendars → **leave as-is** (owner's
keep rule). No repair. If any stay dark long-term they become future dark-venue triage
candidates, but none is a broken scraper today.

---

## Signal 2 — 103 all-sold-out upcoming shows (criterion 11552)

The audit flagged 103 upcoming SeatEngine shows where every ticket is `sold_out=true` (the
largest such cluster across all scrapers). Hypothesis to test: the scraper is coding
unavailable inventory as `sold_out=true` instead of dropping it (soft-fail), making real
future shows look unbuyable.

**Verdict: genuinely sold out, not miscoded. No fix.**

Evidence:
1. **Distribution is benign.** The 103 shows spread across **18 healthy, high-yield clubs**
   (Mic Drop, Hilarities, Cap City, Acme, Wiseguys, Improv venues, …), each a **small
   fraction** of that club's upcoming inventory (e.g. Mic Drop 15/272, Cap City 12/302), at
   plausible 1–3-month lead times. A soft-fail miscode would instead show whole clubs ~100%
   sold out or far-future (6–12 mo) shows all sold out. Neither pattern is present.
2. **The sold-out shows carry full, well-formed inventory** — multiple real priced tiers
   (e.g. Cap City "Special Event: Mojo Brookzz": `$38.22 General Admission` + `$192.44 Couples
   Package`), real show names, and real club-site URLs. A soft-fail produces a single
   `$0 / General Admission` fallback ticket with `sold_out=true`; that is **not** what these
   rows look like.
3. **The scraper code reflects the API faithfully.** In
   `core/clients/seatengine/client.py::_extract_ticket_data`, `sold_out` is set only from the
   API's own fields (`show.sold_out`, `inventory.sold_out`, `inventory.available is False`),
   and inventory with `active is False` is **dropped**, not coded as sold out. There is no
   soft-fail path that fabricates `sold_out=true`.
4. **Live re-scrape confirms current accuracy.** Re-running Cap City (93) fresh returned
   **12 all-sold-out vs 280 all-available, 0 partial** — i.e. ~96% of its shows are correctly
   marked available. If the scraper were blanket-miscoding, nearly all 292 would read
   sold-out. "Special Event: Mojo Brookzz" (a popular multi-night special) remained sold out
   on the live pull, matching the source.

> Note: `partial=0` (no show has some tiers sold and some available) is expected, not a bug —
> SeatEngine's `sold_out` is frequently a show-level flag that applies to all of a show's
> inventories at once.

**Disposition:** the 103 all-sold-out shows are genuine sellouts; the SeatEngine scraper is
correctly reflecting source availability. No change.

---

## Summary

- **Criterion 11551 (5 stale clubs):** all diagnosed — healthy sources, dormant venues; no
  repair. Root cause of the metric is that `stale_30d` keys off show `last_scraped_date`,
  which a 0-show dormant venue never refreshes.
- **Criterion 11552 (103 all-sold-out):** confirmed genuine sellouts; scraper faithfully
  reflects the SeatEngine API; no soft-fail miscoding. No fix.
