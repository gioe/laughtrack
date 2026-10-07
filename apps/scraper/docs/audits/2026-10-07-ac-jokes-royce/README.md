# TASK-4131 — Royce evidence and unresolved postal identity

Status: identity policy resolved by operator; guarded repair in preparation.
No production writes or live persistence run have been performed yet.

On 2026-10-07 the scraper-native Wix HTTP stack fetched the complete source291
feed: 51 events across two pages, with hasMore=false on the last page.
`native-events.json` retains public identity, scheduling, and location fields;
no access token or private dependency data is retained.

The same three reviewed Royce occurrences remain in the source and database:

| Show ID | Native ID | Verified UTC start |
| --- | --- | --- |
| 7898492 | 3a929c46-de3e-443e-a4ea-a9efcb19cac2 | 2026-10-17T00:30:00Z |
| 7898494 | 54f73481-a918-4f0c-8a45-b42a6995f47e | 2026-10-17T23:00:00Z |
| 7898497 | 2634bee1-2f29-42bf-b9a8-d23e175021ea | 2026-10-18T01:00:00Z |

All three still belong to club412, have room The Royce Social Hall, and lack
producer fields. Source291 remains enabled and owned by club412. Its four
reviewed routes (two Resorts rooms, Hi Point, Cove) and producer46 are intact.
No existing Royce club was found by venue-name or the candidate street addresses.

## Address conflict

- The fresh Wix feed and AC Jokes public event page say **2801 Pacific Ave,
  Suite 308**, Atlantic City, NJ08401.
- [Royce official homepage](https://theroyceac.com/) says **2831 Pacific Avenue**,
  with no suite. Native Playwright fetch confirms this text.
- Its linked [official comedy site](https://www.comedyattheroyce.com/) exposes
  EventVenue JSON-LD for venue UUID 3c57e2b2-42fb-4765-a51d-6d277a79d6c8,
  **2831 Boardwalk**, with no suite. Its phone matches the parent venue site.

`official-evidence.json` retains exact public addresses and capture hashes.
The operator permitted omitting the suite from the stored physical venue address.
We use the venue homepage postal address **2831 Pacific Avenue**, with no suite,
and its canonical website https://theroyceac.com/. The shared venue name, Tropicana
location, linked official ticket site, and matching phone establish venue identity.
The AC Jokes full source address **2801 Pacific Avenue, Suite 308** remains an
explicit reviewed routing alias. These differing addresses are not silently
normalized: any changed or missing source suite still fails exact route matching.
Tusk decision context801 records the operator clarification.

## Guarded repair requirements

Capture fresh database state and compare all reviewed native identities before apply. Reuse existing exact-address Wix routing
and shared schema/row/collision/backup helpers in the guarded repair scripts.
Create the task-scoped Royce repair and regression tests, append only the
confirmed route, preserve the existing task4110 markers/routes, and guard all
three exact shows, all seven dependency tables, and source ownership. Preserve
all IDs, native dates, URLs, and room behavior. Run a guarded dry-run before
apply, then validate normal live scraping reuses the repaired IDs and preserves
Resorts/Hi Point/Cove assignments. Suite conflicts must remain held.

October16 is **8:30 PM EDT**, as stated by the fresh event title and startDate.
The 8PM slug is not time evidence. No acceptance criterion is complete yet.
