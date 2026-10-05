# SeatEngine organizer routing — TASK-4109

The account client assigned every performance to its configured organizer club.
Fresh native API snapshots and official event pages revalidated the TASK-4065
cohort. Native show IDs and offset-bearing start timestamps match the stored
identities. Destination addresses come from the physical venues' official sites;
`destinations.json` records those sources and the inferred regional timezones.
Fountain Square Theatre uses its own published 1111 Prospect entrance, distinct
from the umbrella building's 1105 Prospect address.

## Reviewed plan

`plan.json` is the guarded repair input; `dispositions.json` explains each outcome.
The 19 confirmed mismatches move to Hoboken Biergarten (6), Fireside Lounge (3),
White Rabbit Cabaret (9), and Fountain Square Theatre (1), retaining their IDs,
source URLs and UTC instants. Four Willie McBride performances remain on club613
with unchanged venue identity; only producer provenance is added. Two are now
past. The past Tim McLaughlin event's direct API still confirms native identity
and time; its current public URL redirects to the calendar. Its location evidence
is the event-specific September28 capture, not text borrowed from that redirect.

Of the nine original unknowns, two Joe Fenti performances remain biography-only
and six Cinema Grill events retain the unresolved restaurant/theatre entrance
conflict. They are held unchanged. Anthony Locascio6039623 was already absent
before this task; the historical API now names Biergarten but records an October2
cancellation. It stays absent and its route remains held.

Olivia1394784 is the duplicate of1395297: same account444/native370399/time.
The canonical SeatEngine show retains its ID. Identical lineup/tag relationships
are coalesced, distinct relationships are moved, and the duplicate unpriced
General Admission listing is consolidated into its priced General Admission
counterpart. The separate Tier1 offer remains. Original ticket/show IDs and the
first-party alias URL are retained in source metadata and the private recovery
snapshot. Source289 is disabled so the fixed-club JSON-LD path cannot recreate
that duplicate. Club410 remains hidden; the new physical White Rabbit venue is
visible. Organizer clubs613/447/469 are not hidden.

Laugh Tonight stays quarantined: source294 remains disabled and club855's cleared
postal identity remains unchanged. Tommy Davidson835461 moves to verified
Cornerstone in Muncie: native -04 offset and stored instant agree with that city.
Henry Coleman1441452 retains its quarantined club and original timestamp because
the account's -04 offset conflicts with Chicago's -05 local offset; the explicit
API cancellation is recorded without guessing a new time. Darren Brand4340528
remains held because current evidence does not establish the physical venue.

## Routing contract

Only sources with `metadata.seatengine_venue_routes` opt in. The object contains
`account_id`, a real production-company `producer_id`, and `routes` keyed by
native show ID. An approved route contains exact `start_date_time`, destination
`club_id`, `disposition: route`, and an evidence `reason`. Explicit holds use
`disposition: hold` and a reason. The client preserves source-account URLs and
tickets while assigning the destination and both producer provenance fields.

Unknown IDs, changed timestamps, invalid/hidden destinations, disabled sources,
cancelled events, and ambiguous naive wall times are held. A partial hold marks
the result incomplete so successful siblings cannot authorize stale cleanup.
New performances require reviewed routing entries; this change intentionally
makes no address guesses from artist biographies or organizer-level metadata.
The deletion cap remains10 and generic validation/reconciliation are unchanged.

Destination lookup uses `ClubHandler.get_physical_clubs_by_ids`, which reads
visible active clubs without requiring a scraping source. Ordinary scrape-target
selection still requires its configured source. The first live verification
exposed that distinction: all three accounts held safely because the original
lookup excluded source-less destination clubs. A real PostgreSQL pipeline test
reproduced the failure before the dedicated lookup fixed it; separate cases
verify that hidden/inactive destinations remain excluded.

National SeatEngine discovery also preserves cleared city/state/ZIP when an
existing source is disabled with disposition metadata. This closes the future
postal-payload gap recorded in TASK-4070 without re-enabling that account.

## Repair and recovery

Run from `apps/scraper`:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/repair_seatengine_organizer_venues.py \
  --plan docs/audits/2026-10-05-seatengine-routing/plan.json --dry-run
```

Apply requires explicit `--apply --backup /private/path/new.json`. The script
locks and checks the relationship schema and all reviewed before-images, refuses
conflicts, saves complete private pre-images before mutation, and saves an after
snapshot with allocated IDs. Recovery files contain user-linked rows and must
never enter git. A repeat run validates the applied plan rather than repeating
writes. The rollback-only production rehearsal and live verification outcomes
are recorded alongside this document after execution.


## Applied outcome

The production rehearsal rolled back, and a subsequent full-row comparison
verified the original cohort and all seven dependent tables unchanged. Apply
completed successfully; the repeat returned `already_applied: true` without
writes. `apply.json`, `repeat.json` and `post-apply.json` record the exact results.
Destination IDs are90815 White Rabbit,90816 Fountain Square,90817 Biergarten,
90818 Fireside and90819 Cornerstone; real producer IDs are41–44.

The affected cohort is35 stored shows before and34 after the duplicate merge.
Tickets60→59, lineup links32→31 and tags69→66 reflect only the reviewed duplicate
relationships. All756 click rows remain byte-for-byte unchanged. There were no
saved-show, notification or discovery-feature rows in the affected cohort;
those tables were still included in the schema check and recovery snapshot.
All unaffected relationships retain their IDs. Original organizer venue fields
and visibility remain unchanged, and affected club totals match stored rows.
Recovery files are `/private/tmp/task4109-recovery.json` and its `.after.json`
companion (private, mode0600; not committed).

Validation:100 SeatEngine/client/reconciliation tests pass;19 actual PostgreSQL
repair/quarantine/destination tests pass using isolated local temporary tables. Related club
coverage passed216 tests with1 existing skip. The full gate cannot collect due
to missing local `tzdata`; three clean-HEAD prechecks reproduced it with no
flakiness or upstream divergence, so the documented scoped-commit fallback applies.

## Subsequent live verification

The corrected scraper ran against all three accounts on October 5 at
22:25–22:26 UTC: Yardbird updated 8 existing shows, Alameda updated 3, and
Let's Comedy updated 9. Each batch reported zero inserts. The two Joe Fenti
and six Cinema Grill occurrences were explicitly held; incomplete results
remain ineligible for stale reconciliation. Source 294 was not scraped.

The independent post-live query at 22:27 UTC verified fresh scrape timestamps
and `last_scraped_by = seatengine` on all 20 upcoming approved performances,
alongside the exact destination, original URL, UTC instant, room, and both
producer fields. Historical approved assignments also remain correct. All
original dependent-row IDs survive except the explicitly reviewed duplicate
coalescences; all 756 click rows remain byte-for-byte unchanged. The retired
Olivia duplicate remains absent, sources 289/294 remain disabled, organizer
visibility/geography remains unchanged, and club totals match stored shows.
`post-live.json` records the refreshed show IDs and verification outcome.
