# TASK-4127: historical Annoyance performance dispositions

## Outcome

Investigation completed October 7, 2026. Historical ThunderTix calendar queries
resolve the recorded source dates for **two** duplicate-identity pairs. The third
remains unresolved. **No production correction, merge, deletion, identity
backfill, or scraper refresh was performed. All six show rows remain intact.**

This task's deliverable is an evidence-backed disposition, not an executed repair.
The two proposed merges below need a separate guarded repair with a fresh private
backup and relationship migration; this report is not an apply plan. In particular,
do not delete the older Fire & Beer row: it owns 26 of that pair's 27 clicks.

| Pair | Native event / performance | Evidence-backed disposition |
| --- | --- | --- |
| Fire & Beer: 7451272 / 3769502 | 188918 / 3256449 | Merge justified by current historical provider record; proposed survivor **7451272**, whose date is September 19, 2026, **8 p.m. America/Chicago** (`2026-09-20T01:00:00Z`). Retain both until guarded repair. |
| Spitball: 1371908 / 847662 | 263284 / 3249429 | Merge justified by current historical provider record; proposed survivor **1371908**, whose date is May 24, 2026, **6:30 p.m. America/Chicago** (`2026-05-24T23:30:00Z`). Retain both until guarded repair. |
| God Lens Book Release Show & Party: 1024865 / 927780 | 263406 / 3250362 | **Retain unresolved, no survivor selected.** May 16 has supporting public evidence, but no retrieved source binds native performance 3250362 to an authoritative historical date. |

The proposed survivors already have the provider's recorded instant. Choosing
them avoids altering that instant, but does not authorize discarding the other
rows' tickets, tags, clicks, or any newly created relationships. These are
provider schedule records, not proof that a performance actually took place.

## Evidence and conflicting dates

The [September 30 audit](../2026-09-30-annoyance-identity/REPORT.md) explicitly
preserved these six rows outside its then-current calendar capture. The live
database still has both rows in each pair; each has one ticket, and the two
tickets contain the same merchant, event ID, and performance ID. All six
`source_performance_id` values remain null. Generic event URLs alone would not
establish duplicate performance identity.

[source-evidence.json](source-evidence.json) records direct HTTP observations at
15:17 UTC, request URLs, decoded-response SHA-256 digests, actual JSON array
counts, and relevant provider fields. Requests used the scraper's `HttpClient`
with curl-cffi Chrome 124 impersonation and its browser fallback. Historical
calendar request construction was verified directly in
`src/laughtrack/scrapers/implementations/api/thundertix/scraper.py`.

Five weekly windows beginning May 10, May 17, May 24, September 13, and September
20 returned 18, 17, 16, 19, and 23 rows respectively. These are the provider's
returned arrays, not a claim that they enumerate every event that ever existed.

- **Fire & Beer:** the September 20 UTC window contains performance 3256449,
  event 188918, with `start=2026-09-19T20:00:00.000-05:00` and matching ticket
  URL. That agrees with show 7451272. Show 3769502 is stored at 13:00 UTC
  (8 a.m. Chicago) on September 19. The [venue's series page](https://www.theannoyance.com/show/fire-%26-beer%3A-annoyance-house-ensemble)
  also advertises Saturdays at 8 p.m.; it is corroboration, not the historical
  identity proof. The expired order URL now renders upcoming dates.
- **Spitball:** the May 24 window contains performance 3249429, event 263284,
  with `start=2026-05-24T18:30:00.000-05:00` and matching ticket URL. That agrees
  with show 1371908. Show 847662 is stored one week earlier. The [venue page](https://www.theannoyance.com/show/spitball)
  still advertises May 17 at 6:30 p.m., without an explicit year or performance
  ID, and links only the reusable event. The historical ticket URL now renders
  a different performance, 3277845. Neither stale series copy nor the redirected
  checkout date overrides the exact-ID historical calendar record. The two
  sources' disagreement is preserved rather than hidden.
- **God Lens:** show 1024865 is May 16 at 3 p.m. Chicago; show 927780 is May 10
  at 3 p.m. Both carry performance 3250362. The [author's site](https://www.micknapier.com/)
  advertises May 16 at 3 p.m. on a Saturday and links event 263406, but supplies
  neither a year nor the performance ID. The historical calendar windows
  contain no matching performance. The exact ticket URL returns a 404 error
  page. Scoped Wayback CDX and calendar-capture requests returned no captures;
  the availability API returned a 429 page. These probes do not prove that no
  archive exists. They also do not establish cancellation, rescheduling, or
  whether either stored date is a scraper error. Preserve both rows.

The Spitball conflict demonstrates why a plausible venue announcement or the
most recently scraped row is insufficient by itself. No AM/PM correction,
week-offset heuristic, inferred room assignment, or date guess was applied.

## Reproduction and limits

The exact calendar URLs and filtered matching objects are committed in
`source-evidence.json`. Query them as JSON through the scraper HTTP stack;
do not inspect API counts through an HTML-summary tool. The source can change
after this capture. Raw temporary HTML contains unrelated page content and is
not committed; hashes identify the particular decoded responses observed.

Relationship preservation and the read-only verifier are documented in
[PRESERVATION.md](PRESERVATION.md). Before executing either proposed merge,
re-fetch its exact historical record, inspect current foreign keys and full
relationship rows, review survivor/child-row conflict handling, back up privately,
and verify a guarded transaction and idempotent rerun. Leave the God Lens pair
outside any repair unless new performance-specific evidence resolves it.
