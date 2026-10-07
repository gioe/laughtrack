# TASK-4131 — Royce routing and repair evidence

Status: guarded repair applied; corrected live scrape and independent preservation checks passed.

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

Before repair, all three belonged to club412, had room The Royce Social Hall,
and lacked producer fields. Source291 remains enabled and owned by club412. Its four
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
The 8PM slug is not time evidence. The routing regression criterion is complete.

## Applied repair

The new guarded script is `scripts/core/repair_ac_jokes_royce.py`. It reuses the
existing schema locks, exact venue resolution, row snapshots, and 0600 recovery
writer. Its private plan must contain complete before-images and the three raw
native occurrences; the plan and private before/after backup are excluded from Git.
It verifies the exact native-ID-to-show mapping, URL, UTC instant, location, and
confirmed schedule, then requires every protected row to still match.

Nineteen PostgreSQL tests passed using connection-local temporary tables with
rollback cleanup. They cover preservation/idempotence; show, source, inventory,
dependency, venue and schema drift; collisions; failed backup writes; altered
native IDs/dates/slugs; and conflicting address/suite or TBD data.

The production dry-run rolled back. Independent comparison found all192shows,
192tickets,12lineup links,989tags and2826purchase-click rows exactly unchanged.
Apply created physical club **93720**, linked existing producer **46**, and
changed only club_id, production_company_id and scraped_by_organizer_id on the
three approved show IDs. All other show columns and all seven dependency tables
were preserved exactly. Source291 retained ownership, enabled state, previous
routes and metadata; only the Royce route and repair marker were added.
An immediate repeat returned already_applied=true. See rollback-verification.json
and apply-verification.json for sanitized independent comparisons.

Future reruns after legitimate scraping may refuse the old snapshot; that is an
intentional guard. Recovery requires comparing current rows to the private saved
after-image before restoring selected fields. Never restore old TASK4110 backups.

## Live verification and room preservation

The first live check exposed a persistence-boundary defect: ShowHandler removed
the room when it equaled the physical club name. Its subsequent title-based
reconciliation could not match the changed 8PM-to-8:30PM title. That scrape
created duplicate8030992 with an empty room for original7898492.

ShowHandler now preserves native rooms for reviewed Wix routes, recognized by
the Wix scraper key and matching positive producer/organizer IDs supplied by
WixVenueRouter. Other scrapers and unconfigured Wix retain existing suppression.
The regression reproduced the failure before the fix; 54 focused tests then
passed, including two real PostgreSQL upserts across a title change retaining
the original show ID, room, saved-show and purchase-click references.

The repair script's separate --cleanup-live-duplicate mode requires a fresh full
snapshot, unchanged routing metadata, the exact task-created duplicate pair,
matching occurrence identity, and schema coverage. It removes only redundant
tickets/tags already represented on the original. Any other new references or
conflicting child payload refuse cleanup. Twenty-five PostgreSQL repair tests
passed, including cleanup drift and reference guards. A production rollback
dry-run preserved all rows. Apply removed only duplicate8030992, ticket9167558,
and its three redundant tags, retaining original IDs and a private recovery log.

The corrected live run at 2026-10-07T22:24Z processed all 51 native events with
**0 inserts and 51 updates**, with no routing holds. Independent verification
against the original post-repair snapshot confirms the exact same 192 show IDs,
all dates, URLs, rooms, venue assignments, producer attribution and source291
ownership/configuration. All preexisting rows in the seven dependency tables
remain unchanged: 192 tickets, 12 lineup links, 989 tags, and 2826 original
purchase-click rows. One additional purchase click arrived independently.
Expected show enrichment consists only of scrape timestamps, popularity, and
the corrected title on7898492. See live-verification.json and
cleanup-verification.json for sanitized evidence. Missing or conflicting source
suites remain held in regression coverage; matching is not relaxed.
