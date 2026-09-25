# TASK-4051: ThunderTix diagnosis

At pickup on September 25 UTC, The Annoyance Theatre (club 183/source 53) and Visani (club 11600/source 7139) had not refreshed successfully since August 22. Recent production runs exhausted the 180-second club budget with zero output. The initial future cohorts contained 106 and 37 rows respectively.

## Runtime failure

The mandatory endpoint is `/reports/calendar?week=0&start={ts}&end={ts+7d}`. The scraper generates 12 weekly targets by default. Through the actual scraper HTTP stack, all 12 windows returned in 1.38 seconds for Annoyance (309 unique performances, 57 event URLs) and 1.25 seconds for Visani (71 performances, 28 event URLs). These counts precede venue exclusions and past-show filtering.

The former `get_data` awaited optional detail-page pricing before returning performance data. The shared mixin had no request or phase deadline, and evicted failed URL tasks, allowing the same recurring event to be retried in every weekly window. A controlled reproduction on unchanged code showed a never-returning price lookup withholding a healthy calendar performance; a 50 ms test guard cancelled it. Another reproduction made 12 requests for one failed event URL across 12 windows. The original criterion named a test that did not exist; the added regressions reproduce the behavior itself.

Detail responses vary. One Visani HTTP probe returned 403 in 0.047 seconds, while the actual scraper browser retrieved it in 3.424 seconds. Subsequent sampled price requests succeeded in 0.30–1.14 seconds. Full read-only fetches with the fix encountered real 10-second price timeouts but returned Annoyance in 62.31 seconds and Visani in 53.08 seconds. This establishes an unbounded failure path, not that every detail request always hangs. Scheduled-runner behavior still needs verification after merge.

The fix keeps the existing 180-second outer budget. It limits fetching to 150 seconds, each mandatory calendar request to 20 seconds, and optional pricing to a shared 60-second budget, four concurrent requests and 10 seconds per acquired slot. Failures are cached for the run. Optional bot-block diagnostics remain isolated so they cannot incorrectly block reconciliation after a complete healthy calendar. Failed or malformed mandatory calendars raise high-severity errors, preventing an incomplete inventory from authorizing deletion.

## Verified merchant times and stale rows

Visani performance 3249140 serializes `19:00-0500` while its calendar display says 7 pm EDT. The matching current merchant event 263214 advertises September 25 at 7 pm EDT and JSON-LD `2026-09-25T19:00-04:00`. Parsing now validates the displayed date/time/zone against the configured venue IANA timezone instead of trusting the inconsistent raw offset. Missing display fields retain the existing raw parser; conflicting or malformed supplied displays fail safely.

The reviewed repair updates 32 existing rows in place: 27 verified timezone corrections and five Tammy Pescatelli performances rescheduled from October to January 13–16, 2027 with unchanged performance IDs. Visani therefore needs 18 weekly windows; metadata accepts a bounded horizon of 1–26 weeks. Explicit verified music-only title prefixes preserve mixed comedy acts.

Five reviewed rows are retired: unavailable Blue Velvet Lounge, absent November 3 Tuesday Musical Improv, removed Friday late One Funny Lisa Marie performance, and two music-only Visani events. All other history is retained. The repair validates the complete reviewed show/source cohort and exact ticket identities; it saves all seven dependent tables in a private durable backup before commit. Click records keep their IDs through the existing SET NULL relationship.

## Annoyance identity limitation

The filtered Annoyance source contains 280 performances, including 40 pairs with the same club/date/blank-room database key. Thirty existing rows occupy these slots. Ordinary first-wins deduplication would overwrite show 5732294 (Anton Sucks) with Motorcycle Rocketship and show 4910291 (Cryptic) with Famous, Eventually. Venue colors and historical room labels do not establish a trustworthy current room mapping.

A persistence guard rejects conflicting ThunderTix identities before deduplication, including conflicts across batches. Validation errors disable stale reconciliation and preserve existing rows and relationships. Nonconflicting performances can refresh, but these collisions remain an explicit coverage gap tracked by TASK-4081. No synthetic room names are introduced. The runtime repair must not be described as complete Annoyance coverage.

## Evidence

`source-evidence.json` records the public 12-window inventories, request timings, controlled failures and matching merchant time evidence. `visani-18weeks.json` captures the extended horizon; `annoyance-collisions.json` and `room-research-summary.json` record the identity limitation. `reviewed-plan.json` contains public row IDs and guarded dispositions. Private relationship backups remain outside the repository. Production outcomes are recorded separately after the guarded repair and venue runs.
