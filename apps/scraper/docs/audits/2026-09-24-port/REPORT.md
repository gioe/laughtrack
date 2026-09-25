# TASK-4050: Port Comedy calendar recovery

## Diagnosis and source evidence

Club 11482 / source 7054 had 183 stored shows, including 95 future listings at invented local midnight. Last successful refresh was June 30, 2026; five recent runs timed out at 180 seconds with no shows. The Eventim storefront remained behind a Cloudflare challenge. A one-month browser probe returned no pages in 53.66 seconds.

The venue's complete calendar at https://portcomedy.com/calendar/ is server-rendered and supplies 147 distinct ticket event IDs, explicit month/year headings through January 2027, and performance times separate from doors. The homepage has only 134 unique events and omits 13 valid Boiler Room dates; it is not a complete reconciliation source. The recorded fixture retains four real calendar cells, including those distinctions and the year rollover. source-evidence.json records source hashes and selectors; reviewed-plan.json records the exact public cohort and decisions.

## Implementation and production repair

Source 7054 retains its original URL, scraper key, and metadata and adds calendar_url. The scraper fetches the complete official calendar in one request. Missing year/time, conflicting duplicate IDs, orphan cards, empty content, or failures reject the scrape and prevent stale reconciliation. Legacy browser listing and detail enrichment have bounded deadlines; missing detail times no longer become midnight. Detail JSON-LD must match event identity and supply one unambiguous valid time.

The guarded script was rehearsed in a rolled-back production transaction, then applied September 24, 2026. It corrected 83 existing show IDs in place, retired 13 specifically reviewed unsupported future IDs, and left 87 historical rows unchanged. All 3,713 existing click IDs were retained, including SET NULL links from retired shows. Retired-show child records are included in recovery. All seven show foreign-key tables and the exact source/show cohort are guarded.

Private recovery: ~/.tusk/backups/laughtrack/task4050-recovery.json (exclusive creation, mode 0600, fsynced before commit). Never commit this file: it contains user data. Restore verifies exact schema and affected before/after state and refuses drift. The subsequent normal scrape changes that state, so an automatic restore after refresh is expected to refuse and requires a separately reviewed recovery plan.

## Verification

- 24 focused pipeline tests passed, including actual calendar parsing, doors/showtime separation, 2027 year and DST, malformed calendars, identity-matched details, cancellation, bounded concurrency, and failed-fetch diagnostics.
- 22 actual PostgreSQL repair tests passed, covering apply/restore, relationship preservation, schema/cohort drift, history protection, and timestamp-format equivalence without accepting actual timestamp drift.
- Full configured scraper test gate passed in 76.7 seconds for the implementation commit.
- Read-only live get_data produced 147 verified events in 1.4 seconds.
- Normal make scrape-club run at 2026-09-24 23:02 UTC scraped 147 events in 1.00 second and completed persistence in approximately 13 seconds (run key scraper:2026-09-24T19:02:45.662280).
- Persistence produced 142 fresh listings (59 inserts, 83 updates). Every persisted upcoming time matched the source; no invented local-midnight times remained. At verification after 00:00 UTC, 141 were still upcoming and the first Rosebud Baker performance had just started. Click count increased naturally to 3,714; no existing clicks were lost.

## Remaining findings

Five same-time event pairs collapse under the existing club/date/room key: Oct 11 New Material Night / Rob Stant; Nov 8 New Material Night / Ahmed Al-kadri; Nov 11 Boiler Room / Jake Velazquez; Nov 15 New Material Night / Ronnie Fleming; Dec 12 Gabby Bryan / David Cross. Tracked separately as TASK-4080: establish source correctness or actual rooms before changing identity. This is why 147 source IDs yield 142 persisted performances. No room assignments were invented.

Scheduled verification remains explicitly deferred under criterion 13244. Scheduled run 36074286702 started at 2026-09-24T23:45:14Z on the pre-fix commit aa8317d54 and cannot validate this implementation. Observe a later scheduled run whose head includes TASK-4050; record Port success/error, runtime, raw/persisted source counts, freshness and remaining local-midnight records, then clear the deferral. The successful local production run is not evidence of scheduler success.
