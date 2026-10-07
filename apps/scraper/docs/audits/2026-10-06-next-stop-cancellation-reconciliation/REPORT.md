# TASK-4122 — Next Stop explicit cancellation reconciliation

## Status

The runtime cancellation lifecycle is implemented: 168 focused tests and 11 isolated PostgreSQL integration tests pass. Three exact-identity production rows were marked cancelled and independently verified read-only at `2026-10-06T23:58:52Z`. All other show fields and all child records are unchanged. The full-suite gate is blocked at collection by the pre-existing missing `tzdata` package, reproduced in all three clean-HEAD prechecks without divergence or flakiness.

## Reviewed evidence and scope

Six pages were refreshed at approximately `2026-10-06T23:51:07Z` through the scraper's HTTP stack. [source-evidence.json](source-evidence.json) records the retained source evidence, including requested/final URLs, status codes, redirect counts, hashes, and event identity/status fields. The HTTP client returned empty redirect-history arrays; positive redirect counts and differing final URLs establish the observed redirects.

| Existing show | Source result | Disposition |
| --- | --- | --- |
| Sociology Coffee Bar `5722554` | HTTP 200, no redirect; explicit main-event cancellation at the stored URL/date | Flagged cancelled; independently verified |
| Hudson's on Main `5960094` | HTTP 200, no redirect; explicit main-event cancellation at the stored URL/date | Flagged cancelled; independently verified |
| Pinfish Entertainment `6213884` | HTTP 200, no redirect; explicit main-event cancellation at the stored URL/date | Flagged cancelled; independently verified |
| Formosa Winery `6311574` | November 7 URL redirects to a cancelled November 6 event | Hold; do not transfer cancellation across the redirect/date change |
| Big Beaver Brewing `3590689` | Old 7pm URL redirects to its scheduled 7:30pm performance | Scheduled/reschedule control; no cancellation |
| Xanadu Astoria `7557421` | HTTP 404, no verified main event | Missing-page control; no cancellation inference |

The private six-show before-image contains six tickets, 11 lineup relationships, 14 show tags, and 112 ticket-click rows. Saved-show, sent-notification, and discovery-snapshot tables are empty for this production cohort. The independent local integration fixture populates all seven child families, including those empty in production, so their preservation is tested rather than assumed.

## Identity and write contract

Only an explicit `EventCancelled` main event is eligible. Its requested URL, HTML canonical URL, and JSON-LD event URL must agree. Missing status, scheduled status, missing pages, failed fetches, suggested events, and redirect destinations are not cancellation authority for the stored original.

The scraper matches the evidence to exactly one existing Next Stop row using producer and scraper ownership, exact source URL and UTC instant, normalized main title and physical venue identity, and any supplied native event UUID. Street-only stored addresses may match the exact source street address; the postal code must also agree. This is not fuzzy venue matching. An ambiguous match or conflicting scheduled evidence is held.

The resulting immutable cancellation intent contains the observed show ID, producer/scraper, date, URL, native identity, title, and venue name/address/postal code. The handler locks only the referenced show and venue rows, rechecks the full expected identity and uniqueness inside the write transaction, and updates only `shows.is_cancelled`. It does not delete shows or children, invent an event, merge references, or rewrite time/venue/URLs. A changed identity aborts cancellation; the result processor suppresses stale cleanup on that error.

Cancellation is persisted before stale reconciliation. Both existing stale-delete families already require `is_cancelled = false`, so a confirmed cancellation survives subsequent missing-from-feed cleanup. The web public/detail queries also require a non-cancelled show, excluding the preserved row from public discovery without removing its history.

## Lifecycle verification

[test_next_stop_cancellation_lifecycle.py](../../../tests/integration/test_next_stop_cancellation_lifecycle.py) executes the real `ShowHandler` upsert SQL, source cancellation extractor/matcher, cancellation handler, result processor, and both scraper-key/organizer stale predicates against a local PostgreSQL schema. Every test rolls back. A local-host guard refuses a nonlocal `TEST_DATABASE_URL`; there is no production rehearsal or global production table lock in this verification.

The lifecycle test covers both legacy slot identity and native performance identity:

1. Persist a scheduled show through the actual handler and attach nonempty ticket, lineup, tag, saved-show, notification, discovery-snapshot, and click rows.
2. Make the show deliberately stale, then process explicit cancellation. If cancellation happened after cleanup, that row would be deleted; the test instead requires its full row image to differ only by the cancellation flag.
3. Require every child ID and complete payload to remain identical. Repeat cancellation and require an identical full snapshot.
4. Execute the actual count/delete SQL for both stale-reconciliation families and prove that neither can remove the cancelled show.
5. Perform an ordinary upsert and prove that the same show ID stays cancelled with all children preserved.

Controls cover scheduled status, missing status, changed source date, a redirect, a failed/empty fetch, and ambiguous stored matches. They produce no cancellation writes. Transaction-time changes to the title, native identity, or venue address cause a guarded failure and prevent stale cleanup.

The visibility assertion is a SQL-level contract check tied to the repository's `NON_CANCELLED_SHOW_WHERE` constant and the actual `findShowById` predicate. It is not an HTTP/browser test of the public application. Only database connection acquisition is redirected to the isolated fixture; cancellation matching and persistence are not mocked.

Run from `apps/scraper/` with a local PostgreSQL database:

```bash
TEST_DATABASE_URL=postgresql://localhost/postgres .venv/bin/python -m pytest tests/integration/test_next_stop_cancellation_lifecycle.py -q
```

Without `TEST_DATABASE_URL`, database integration cases skip safely. The verified run passed all 11 cases.

## Reactivation policy

Cancellation is sticky. Ordinary scheduled ingestion or a normal upsert must not set `is_cancelled` back to false, even if a source page later changes status. Reactivation requires a separate manual review of fresh authoritative evidence for the same event, source ownership, physical venue, and intended date, followed by an explicit guarded update with a before-image and audit trail. A redirect, missing page, successful fetch, or absence of a cancellation marker is insufficient.

## Production application and verification

The actual extractor/matcher selected exactly `5722554`, `5960094`, and `6213884` from fresh captured source HTML and current stored identities. The runtime handler applied only `shows.is_cancelled = true` in a transaction with a three-second lock timeout and ten-second statement timeout. A durable private before-image was saved before mutation, with an after-image before commit. A separate read-only transaction then reproduced the entire after-image exactly.

[production-receipt.json](production-receipt.json) records the public receipt: all six show IDs remain, six tickets, 11 lineup rows, 14 tags, and 112 clicks are unchanged; the three other relationship families remain empty in this cohort. All 41 previously confirmed cancellations remain flagged, for 44 total. Formosa, Big Beaver, and Xanadu remain untouched. Row locks lasted 0.346 seconds; the operation including verification took 1.413 seconds. There were no global table locks or production repair/restore rehearsals.

Private recovery images remain at `/private/tmp/task4122-production-cancellation.before.private.json` and `.after.private.json`, mode 0600, outside Git. The production mutation was applied once; repeated cancellation and cleanup are proven in the isolated PostgreSQL tests rather than by repeating writes on production. Reactivation remains a separate reviewed operation under the policy above.
