# Sports Drink omission audit — September 28, 2026

TASK-4064 explains the 85 stale-show candidates reported by TASK-4043's September 24 scrape. The evidence supports cancellations and source-linked schedule changes, not a missing listing page or incorrect source attribution. No production rows were changed; the normal deletion cap remains 10.

| Classification | Stored rows | Disposition |
| --- | ---: | --- |
| Explicit cancellation notice | 56 | Eligible for guarded, freshly revalidated cleanup |
| Legacy URL redirects to a rescheduled, already stored Tixologi event | 28 | Retire only the obsolete row; preserve its identified replacement |
| HTTP 404 without explicit cancellation or replacement | 1 | Hold: show 506917 |

`candidates.jsonl` contains every original stored field, requested URL, retrieval time, source HTML digest, visible ticket CTA, JSON-LD status, classification and rationale for each of the 85 records. Redirected candidates also include the final response URL/status, current listing and replacement show IDs. A 404 alone is not evidence of cancellation.

## Cohort and source comparison

The read-only production query selected club 653 rows after the original cutoff:

```sql
SELECT id, name, date, show_page_url, room, last_scraped_date, last_scraped_by
FROM shows
WHERE club_id = 653 AND date > '2026-09-24T15:49:37Z'
ORDER BY date, id;
```

The 220 surviving rows partition exactly into 85 legacy OpenDate URLs last refreshed before that cutoff and 135 Tixologi URLs refreshed afterward. All have source `sports_drink` and empty room. This reconstructs the original 85-row cohort from surviving state and the recorded cap count; it is not an archived September 24 list of candidate IDs. At the fixed September 28 12:00 UTC comparison cutoff, 84 of the 85 legacy rows are still future shows; one has elapsed.

Source 249 points to `https://app.opendate.io/v/sports-drink-1939?per_page=500`. The current page contains 130 cards, and the actual SportsDrinkExtractor extracts all 130. Exactly 129 URL/UTC-time pairs match stored future Tixologi performances. The other six of the 135 stored Tixologi performances have elapsed since September 24. The remaining extracted card is the purchase confirmation described below. None of the legacy URL/time pairs appears in the current listing.

Pagination checks using the scraper's HTTP stack return 20 cards for `per_page=20`, the identical ordered 130 identities for both `per_page=500` and `per_page=1000`, and zero for `per_page=500&page=2`. The first 20 identities agree. This establishes completeness for the observed source responses; it cannot prove the venue's own calendar contains every real-world performance. The historical log recorded 136 parsed / 135 saved, consistent with six subsequently elapsed performances plus the same non-event card.

All 85 legacy detail URLs were fetched with the actual scraper HttpClient (curl-cffi with browser fallback), with requests paced one second apart. The listing was initially captured with the scraper's PlaywrightBrowser. `pagination.json` retains response hashes and extracted identities; `listing-cards.html` retains sanitized card structure that the real extractor can replay. Full pages, form tokens and session data are intentionally not committed.

## What changed at the source

All 56 cancellation records have a primary ticket CTA reading **THIS EVENT HAS BEEN CANCELED**, despite their JSON-LD still reporting `EventScheduled`. The audit records both signals and uses the explicit visible cancellation notice. These are 56 stored rows, not 56 distinct source event IDs: legacy OpenDate event 652837 appears in both show 506984 and 1094661 at different timestamps.

All 28 non-404 remaining URLs return HTTP 200 after redirecting to a Tixologi URL present in the current listing. Every replacement has a different timestamp and is already stored. This is direct source linkage, not fuzzy matching by title:

- Thirteen Community Night rows move from Tuesday 19:00 to Wednesday 18:30 local time.
- Thirteen Tropical Trivia rows move from Wednesday 19:00 to 19:30 local time.
- Maggie Winters, show 2445150, moves from October 21 at 21:00 to January 21, 2027 at 21:00 local time; the old URL redirects to Tixologi event 13749.
- Burn This Records, show 2445180, moves from November 12 at 20:00 to November 16 at 20:00 local time; the old URL redirects to Tixologi event 13747.

Show 506917, Open Gym on September 30 at 20:30 local time, returns an actual HTTP 404 and a custom not-found page. It has neither the cancellation CTA nor an identified current replacement. Preserve it pending stronger evidence.

The persistence identity includes club, UTC date and room, so changing a date creates a new stored performance while the obsolete timestamp remains until reconciliation. The cap correctly stopped the large historical cleanup batch. No evidence found here supports changing attribution or raising the cap.

## Separate ongoing blocker: purchase confirmation

The source advertises **Thank You For Your Purchase!!!** at `2099-12-31T18:00:00Z`. It is emitted as a show and rejected by the existing 18-month date bound. Current ScrapingResultProcessor skips reconciliation whenever persistence reports validation errors, before reaching the deletion-count guard. Thus the historical cap warning and today's validation-error guard are distinct observations; this audit does not claim a fresh production scrape reached the cap.

TASK-4108 will exclude this verified non-event before persistence while preserving ordinary invalid-date checks and the generic incomplete-batch guard. The 129 actual future performances must remain intact.

## Safe disposition and follow-up

TASK-4107 owns a bounded cleanup of the 56 cancellation rows and 28 obsolete schedule rows after fresh source revalidation. The manifest is a review input, not an executable deletion authorization or an unconditional ID list:

1. Refresh source evidence and compare each stored row's source, URL, timestamp, room and last-scraped state. Hold changed, ambiguous or now-past records for explicit disposition; do not silently include them in future-show cleanup.
2. Preserve show 506917. Confirm all 28 exact replacements still exist before retiring their predecessors. Account for the two stored rows sharing OpenDate event 652837.
3. Inspect dependent tickets, lineups, saved-show references and other foreign keys; save recoverable before-images. Publish exact retire/hold sets and dependent-row impact.
4. Apply only the reviewed set with identity predicates, transaction and row-count guards, then verify every retained replacement and held row. Do not change or chunk around the normal reconciliation cap.
5. Run a subsequent live scrape and record valid output, persistence errors and reconciliation outcome. The purchase-confirmation fix has its own live-scrape criterion.

The two follow-ups have no required execution dependency: bounded manual remediation can be verified while documenting the known validation blocker, and filtering the placeholder still leaves the cap protecting the large stale set. Neither task may bypass those safeguards to report success. Cleanup scope is the audit/remediation directory; prevention scope is the Sports Drink implementation, its tests and audit evidence.

No scraper repair was made in this investigation, so the task's conditional post-repair live scrape does not apply yet. All network and production database activity here was read-only. The follow-ups require live verification after their changes.

## Reproduce and validate

From `apps/scraper`, using the project's Python environment:

```sh
PYTHONPATH=src:. .venv/bin/python3 docs/audits/2026-09-28-sports-drink-omissions/replay.py
PYTHONPATH=src:. .venv/bin/python3 -m pytest -q \
  tests/scrapers/implementations/venues/sports_drink/test_pipeline_smoke.py \
  tests/utilities/domain/scraper/test_result_processor.py \
  tests/core/entities/show/test_handler_stale_reconciliation.py
```

The offline replay checks file hashes, all 85 preserved candidate identities, 56 contradictory cancellation signals, all 28 exact stored replacements, the held 404, actual extractor/time-parser output, pagination and the unchanged default cap. It performs no network or database operations. The focused regression suite passed all 74 tests, including cap refusal and persistence-error cleanup prevention.
