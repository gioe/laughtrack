# AC Jokes physical venue routing — TASK-4110

The AC Jokes Wix account lists performances at several physical venues. Source
291 remains enabled on club 412 (AC Jokes at Resorts); assigning every event to
that club previously misplaced Hi Point Pub and Cove performances.

## Reviewed evidence and disposition

`native-events.json` captures all 52 events from two complete pages of the live
Wix paginated-events viewer feed on 2026-10-05, including structured addresses,
native occurrence IDs, UTC times, and source slugs. `destinations.json` records
successful fetches and hashes of the physical venues' official HTTPS sites.
The native Wix address and the official venue address agree:

| Physical venue | Address | Disposition |
| --- | --- | --- |
| Resorts / Starlight Ballroom | 1133 Boardwalk, Atlantic City, NJ 08401 | Keep club 412 |
| Resorts / Directors Room | 1133 Boardwalk, Atlantic City, NJ 08401 | Keep club 412 |
| Hi Point Pub | 5 North Shore Road, Absecon, NJ 08201 | Create verified physical club |
| The Cove Restaurant | 3700 Brigantine Boulevard, Brigantine, NJ 08203 | Create verified physical club |

Official references: [Hi Point Pub](https://reddogs-hipointpub.com/) and
[The Cove](https://www.thecovebrig.com/location/the-cove/).

`dispositions.json` reconciles the original 44-show audit with the fresh feed and
database. Shows 6537828 and 6537839 belong at Hi Point; 7475796 belongs at Cove.
Show 6537818 is absent from both the database and current upcoming feed. It is
not recreated, and absence is not interpreted as proof of cancellation.
All 40 previously correct Resorts shows remain at club 412. The repair also
guards every other existing club-412 show (192 total before repair).

Three newly observed Royce Social Hall occurrences are outside the four-ID
repair cohort. They are explicitly held by routing and left unchanged in the
database pending separate venue/occurrence review. Their IDs and fresh evidence
are included in `dispositions.json`.

## Source routing contract

Source 291 metadata now contains `wix_venue_routes`: source ID, Wix component ID,
a real `production_companies` ID, and reviewed location-to-club routes. A route
matches location name, country, state, city, street number/name, apartment/suite,
and ZIP. Case and whitespace are normalized; ZIP+4 is reduced to five digits.
No name-only or fuzzy cross-city lookup is performed. The active, visible
physical clubs are loaded independently of whether they own scraping sources.

Both Resorts room names map to club 412; Hi Point and Cove map to their physical
clubs. AC Jokes remains the producer and scraping organizer. The original source
club supplies event/ticket URLs, while the physical club supplies venue identity.
Existing room identity behavior remains in ShowHandler: blank legacy Resorts
rooms and populated offsite rooms reuse their existing occurrences.

Unknown/incomplete locations, invalid route configuration, unavailable venues,
malformed records, and partial pagination produce errors that suppress stale
reconciliation. Reviewed events can still update while the three Royce events
are held. Unconfigured fixed-venue Wix sources retain their existing behavior.

## Guarded repair and recovery

From `apps/scraper`, preview the reviewed plan:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/repair_ac_jokes_venues.py \
  --plan docs/audits/2026-10-05-ac-jokes-routing/plan.json --dry-run
```

Apply requires `--apply --backup /private/path/new-recovery.json`. The script
locks the relevant schema, verifies the current full cohort and source state,
refuses occupied destination slots or schema drift, and writes a private 0600
before snapshot before changing any data. It changes only physical club and two
producer provenance fields on the three reviewed shows; source 291 receives
routing metadata. It creates the two physical clubs, one production company,
and producer-to-venue relationships, then refreshes venue show counts.

All show IDs, other show columns, and all seven dependent relationship tables
must compare equal before the transaction can commit. A plan digest makes an
immediate repeat a verified no-op. Later legitimate scrape changes may cause
the old repair plan to refuse execution; refresh evidence instead of bypassing
its guards. Dry-runs roll back rows, although PostgreSQL sequences can advance.

Private recovery files contain full before/after rows and resolved IDs. Keep
them outside version control; only sanitized counts, public show fields, and
verification results belong in this directory. Recovery requires comparing the
current rows to the saved after image before restoring the reviewed before
fields and metadata transactionally. Do not blindly restore after later writes,
or remove new venue/producer records that have acquired dependencies.

## Verification

The production dry-run was independently checked against the original snapshot:
all 192 shows, 192 tickets, 12 lineup links, 989 tags, and 2,792 ticket-click rows
were unchanged. See `rollback-verification.json`.

Focused routing/physical-club/stale-reconciliation/deduplication checks passed
(50 tests); guarded repair coverage adds 10 passing tests with real PostgreSQL.
The parent independently reran the 26 routing/repair tests successfully.
The full scraper gate stops during collection because the shared environment
lacks `tzdata`; three clean-base prechecks reproduced the same failure without
upstream divergence or flakiness. This limitation is unrelated to these changes.

Production apply, immediate idempotence, and subsequent live-scrape outcomes are
recorded in the adjacent sanitized result and verification files. Live validation
uses the normal scraper command, `make scrape-club-id ID=412`.
