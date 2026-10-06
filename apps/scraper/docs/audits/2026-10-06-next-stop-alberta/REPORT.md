# Next Stop Comedy Alberta wall times — TASK-4119

## Evidence gathered before repair

On October 6, 2026, the scraper's own HttpClient fetched all 19 distinct future
Alberta event URLs represented by 26 production rows. A second venue inventory
using Alberta addresses/state as well as timezone found the same four venues.
`source-evidence.json` records requested/canonical URLs, native event IDs,
matching currentEventId, venue addresses, advertised header, JSON-LD, and HTML
SHA-256. Full responses remain private temporary evidence.

The [Alberta government](https://www.alberta.ca/albertas-new-time-system-abt)
confirms permanent UTC−6 beginning November 2026. The previous September 29
source audit retained obsolete −07 offsets for the two March events; the source
now publishes −06 for every reviewed event. Its independently visible header
still advertises 7 p.m. for both March events, with seating at 6:30 p.m.

| Canonical show | Venue / local date | Advertised time | Correct UTC | Duplicate to merge |
| --- | --- | --- | --- | --- |
| 4168927 | Big Beaver / 2026-11-21 | 19:00 | 2026-11-22 01:00Z | 7743583 |
| 4168928 | Big Beaver / 2026-12-31 | 20:00 | 2027-01-01 02:00Z | 7743584 |
| 4168929 | Big Beaver / 2027-01-16 | 19:00 | 2027-01-17 01:00Z | 7743585 |
| 4944796 | Leduc / 2026-11-20 | 19:00 | 2026-11-21 01:00Z | 7744008 |
| 4944798 | Leduc / 2027-01-15 | 19:00 | 2027-01-16 01:00Z | 7744010 |
| 4168930 | Big Beaver / 2027-02-13 | 20:00 | 2027-02-14 02:00Z | — |
| 3591192 | Leduc / 2027-02-13 | 20:00 | 2027-02-14 02:00Z | — |
| 4168931 | Big Beaver / 2027-03-13 | 19:00 | 2027-03-14 01:00Z | — |
| 4944800 | Leduc / 2027-03-12 | 19:00 | 2027-03-13 01:00Z | — |

## Explicit holds and controls

Leduc New Year's Eve currently advertises 19:00−06. Its three stored rows
3591191, 4944797 and 7744009 include conflicting General Admission prices
52 versus 47. A timestamp-only repair cannot merge those records losslessly
under the unique show/type ticket key. All three are held unchanged for a
separate ticket-history disposition; the safe repair must reject that conflict.

Big Beaver October 24's old 7pm URL now resolves to the same native event as
its 7:30pm URL (native ID 8c4e9da7-24a7-4f8d-8ddd-4081894e1e81).
Rows 3590689 and 4944445 require a separate reschedule/URL-alias reconciliation,
not a winter-offset correction, and remain unchanged.

Many Horses and all five Glitch events already agree with source instants.
October Leduc and Big Beaver controls retain their valid explicit offsets.
No global hour shift, venue timezone change or source configuration change is
supported. TASK-4120 separately covers stale browser timezone data.

## Guarded implementation

The reviewed plan includes all 20 future rows at the two affected venues, with
exact before-images, organizer identity and venue guards. The repair locks the
schema and data cohort, rejects unknown children/new rows/destination collisions,
and retains historical canonical show IDs. Identical child aliases may coalesce;
differing business fields abort. All click IDs and payloads are retained, with
only duplicate show references repointed to the same canonical event.

Shows, venues and production_companies have no metadata column. Next Stop is
routed directly from organizer 35 and has no scraping_sources row. Therefore the
convention's metadata marker is represented by immutable plan/before/after hashes
in durable private recovery files; no artificial source row is created.

Apply requires exclusive mode-0600 backup files. Restore requires the exact
schema and complete after-image, restores deleted aliases, and refuses drift.
Dry-run executes the same transaction and rolls it back. Aggregate venue counts
are outside the timestamp changes; all venue fields remain unchanged.

Ingestion correction requires a matched main-event Flight identity, Edmonton
zone, Alberta/Canada address, obsolete −07 after November 2026, and exactly
matching advertised date/time in the main heading's captured DOM container.
Seating, nearby cards, conflicts, missing evidence and valid offsets cannot
trigger correction. The corrected datetime stays aware-local. ZoneInfo is used
because the shared developer pytz remains stale; TASK-4073 already pins updated
production timezone dependencies.

## Validation

62 Next Stop tests pass, including 39 timezone-selected cases. The two minimal
fixtures retain the real captured DOM and disclose that historical −07 offsets
are simulated from the October 6 source's current −06 value. All 19 fresh pages
replay unchanged at their valid current offsets. Thirteen real PostgreSQL tests
cover repair, rollback/reapply, dry-run, drift, schema changes and loss prevention.

The production dry run passed and rolled back: 20 → 15 show rows, 20 → 15 tickets,
41 → 31 tags through equivalent duplicate coalescence; all 6 lineup rows and all
342 click records retained. Production application is complete; production-receipt.json verifies all nine
instants, no duplicate URLs in the corrected cohort, and all click payloads/IDs.
rehearsal-receipt.json records exact rollback/reapply and real shared ingestion
upserts reusing all nine canonical IDs inside a rolled-back transaction.
Private recovery files are /private/tmp/task4119-production-recovery.json and
its .after.json companion; never commit them. TASK-4121 context785 and criterion
13469 explicitly retain both held cases.

The full scraper gate stops during collection because the shared environment
lacks tzdata. Three clean-HEAD precheck runs reproduced this unchanged baseline
failure with no upstream divergence or flakiness. The documented path-limited
commit recovery applies; focused tests and real database checks above are green.
