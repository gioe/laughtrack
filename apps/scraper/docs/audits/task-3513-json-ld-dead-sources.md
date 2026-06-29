# TASK-3513 — json_ld "dead sources": 9 comedy clubs with 0 upcoming shows

**Date:** 2026-06-29
**Source:** 2026-06-29 scraping-data audit (section 3).

## Headline

The premise — "a coherent cluster of dead json_ld sources ⇒ json_ld extractor drift" —
is **mostly wrong**. The json_ld extractor is healthy (it faithfully parses every JSON-LD
`Event` present and applies no date filter). The 9 clubs split into **four distinct
root causes**, only one of which is an extractor defect:

| # | club | jsonld events (live) | max date | root cause | disposition |
|--:|------|---------------------:|----------|-----------|-------------|
| 13 | Eastville Comedy Club Brooklyn | 48 | 2026-06-28 | current-month rolling window, caught at month-end | dormant-at-month-boundary, real venue → re-check after July rollover |
| 455 | Blue Ridge Comedy Club | 19 | 2026-06-26 | current-month rolling window | same as 13 |
| 1350 | Brew HaHa Comedy at River | 10 | 2026-06-28 | current-month rolling window | same as 13 |
| 48 | Tribeca Comedy Lounge | 2 | 2026-06-06 | near-empty / stale calendar (shared NYC platform) | needs per-venue re-onboard |
| 49 | Dark Horse Comedy Club | 2 | 2026-06-06 | near-empty / stale calendar (shared NYC platform) | needs per-venue re-onboard |
| 50 | Midtown Comedy Club | 2 | 2026-06-06 | near-empty / stale calendar (shared NYC platform) | needs per-venue re-onboard |
| 1058 | Traverse City Comedy Club | 2 (Aug 21/22) | 2026-08-22 | **relative event URLs dropped on validation — FIXED** | extractor hardened (this task) |
| 11438 | The Dinner Detective St. Paul | 0 | — | source page has no per-event JSON-LD | needs source re-point |
| 11459 | The Hive Black Box Theater | 0 | — | source page has no per-event JSON-LD | needs source re-point |

## Root cause detail (criterion 11554)

**Not generalized extractor drift.** Each cluster:

1. **Current-month rolling window (13, 455, 1350).** These venues' calendar pages expose
   JSON-LD for only the **current calendar month**. The audit ran on **2026-06-29** — the
   second-to-last day of June — so the JSON-LD listed only June events, all now in the past
   (e.g. Eastville: 48 events, June 3–28; the venue has 1088 historical shows and sells
   tickets actively). Mid-month the same page yields upcoming events (which is why their run
   history shows `max_shows_seen` up to 48). This is a **month-boundary false-positive** in
   the audit: these venues will repopulate when the calendar rolls to July. They are real,
   active venues — **do not retire**. Worth re-checking after the rollover before any
   re-onboard work, and a candidate for an audit-tool refinement (flag "all-past json_ld" as
   month-boundary noise rather than a dead source).

2. **Near-empty / stale calendars (48, 49, 50).** The three Manhattan clubs share a website
   template (`www.<name>.com/calendar`) and each currently exposes only **2 JSON-LD events,
   max 2026-06-06** (3+ weeks stale, no future). The extractor parses them correctly; the
   sites themselves carry almost no event markup now. These need a per-venue re-probe to find
   where their upcoming shows are sold (re-onboard), not an extractor change.

3. **Relative event URLs dropped on validation (1058).** Traverse City Comedy Club's source
   (`mynorthtickets.com`) emits **root-relative** event URLs (`"url": "/events/<slug>"`). The
   json_ld pipeline carried these straight through to `Show.show_page_url` and the ticket
   `purchase_url`, where Show validation rejected them ("must be a valid URL format") and
   **both upcoming shows (Aug 21 & 22) were silently dropped** every night. This is a genuine,
   generalizable extractor gap. **Fixed in this task** — see below.

4. **No per-event JSON-LD on the source page (11438, 11459).** The Dinner Detective St. Paul
   and The Hive source pages expose **zero** JSON-LD `Event` blocks (JS-rendered or wrong
   URL). The extractor has nothing to parse. These need their source re-pointed, not an
   extractor fix. (11438 was also triaged as dormant under TASK-3511.)

## Fix shipped (criteria 11553 for 1058 + 11554 hardening)

`EventExtractor.extract_events(..., base_url=<fetched page url>)` now resolves **root-relative
`url` and `offers.url`** values against the page they were fetched from (mirroring the
existing `urljoin(calendar_url, ...)` used for detail-URL discovery). Absolute URLs are left
untouched (no-op for the common case); when `base_url` is absent the prior behavior is
preserved. The json_ld scraper passes the fetched `normalized_url` as `base_url`.

- Files: `scrapers/implementations/json_ld/extractor.py`,
  `scrapers/implementations/json_ld/scraper.py`,
  `tests/scrapers/implementations/json_ld/test_event_extractor.py` (4 new tests).
- Verified live: Traverse City's 2 future events now resolve to absolute URLs and pass Show
  validation ("All 2 shows are valid") instead of being dropped. (A separate, pre-existing
  batch-insert quirk only reproduces under a mixed-module local harness and not on the
  nightly, which persists shows from `main` daily — out of scope here.)

This hardening recovers any json_ld venue whose markup emits relative event/offer URLs, not
just Traverse City.

## Per-club disposition (criterion 11553)

- **1058 Traverse City** — FIXED (extractor now resolves its relative URLs).
- **13 Eastville, 455 Blue Ridge, 1350 Brew HaHa** — real active venues; 0-upcoming is a
  month-end snapshot of a current-month JSON-LD window. **Keep**, re-check after the July
  rollover. No retire.
- **48 Tribeca, 49 Dark Horse, 50 Midtown** — calendars near-empty/stale; need a per-venue
  re-onboard to locate the current upcoming-show source. **Keep**, follow-up filed.
- **11438 Dinner Detective St. Paul, 11459 The Hive** — source pages expose no JSON-LD;
  need their source re-pointed. **Keep**, follow-up filed.

No venue was retired — all 9 are real comedy venues (owner keep-rule).
