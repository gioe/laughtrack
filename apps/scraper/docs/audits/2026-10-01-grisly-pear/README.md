# TASK-4086: Grisly Pear metadata recovery

Verified on October 1, 2026, using the production-configured scraper HTTP stack,
normal BaseScraper pipeline, Show validation, and normal ShowService persistence.
This was a local stack verification, not a GitHub Actions dispatch. A full
scheduled persistence run would also add newly listed performances; this repair
was deliberately bounded to source-matched existing records.

## Results

| Venue | Live performances | Explicitly named lineups | Known base prices |
| --- | ---: | ---: | ---: |
| Greenwich Village (6) | 101 | 97 | 101 |
| Midtown (7) | 36 | 23 | 35 |

Both scrapes returned HTTP 200 with no recorded fetch failures. Of 137 live
performances, 116 matched existing club/date/room identities. Those 116 were
refreshed; 21 newly listed performances were not inserted by this repair.

The refresh restored 452 canonical lineup links on 104 shows and 116 General
Admission base prices. The source supplied 495 name entries: the existing
ingestion filter suppressed 43 `And More!` placeholders and resolved the existing
`Talent Harris Jr` alias to `Talent Harris Jr.`. Twelve explicit source-named
performers were inserted through the standard comedian handler. No people were
inferred from generic show titles.

Post-write comparison preserved all 1,987 show IDs and all 2,163 ticket IDs.
All 1,871 unmatched records, including their lineups, tickets, URLs, and scrape
timestamps, were unchanged. The two unmatched future records were preserved.
Show 6331162 still redirects from October 8 to October 1; none of that target's
metadata was applied to the October 8 record.

## Durable behavior and regression checks

The scraper accepts legacy and current dated URL formats, fetches event details,
and requires the detail date/time, physical venue, and canonical URL date to
agree. Explicit JSON-LD/Featuring names pass through the normal lineup factory;
Special Guest is excluded. Unnamed events remain unnamed. Conflicting aliases
and failed/mismatched details record incomplete diagnostics to block stale
reconciliation. Same-venue/time aliases are deduplicated.

Price extraction requires current General Admission purchase controls. It uses
the base amount, not the fee-inclusive total; absent inventory stays unknown.
Historical real fixtures cover base $10 versus total $12.37, base $20 versus
total $23.24, sales-ended inventory, and redirected dates.

All 16 focused tests passed; the full scraper commit gate passed in 80.3 seconds.
Tests freeze the clock for captured calendar fixtures. Existing TASK-4055 and
TASK-4056 HTML fixtures are reused. Fresh raw HTML remains temporary because it
contains session-specific fields; public metadata and capture hashes are retained
here instead.

`live-preview.json` records source output before persistence filtering;
`refreshed-performances.json` records each repaired identity and persisted names;
`verification.json` records preservation checks, diagnostics, and source hashes.
