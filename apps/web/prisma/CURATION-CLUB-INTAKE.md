# Club intake policy

TASK-4180 extends the durable curation ledger to club discovery and publication.
Only a single, explicitly approved venue identity can admit a public club or
write its shows and scraping sources. Missing policy raises; unresolved and
ambiguous identities stay pending with inspectable observations.

## Identity

Keys are append-only: `club-id:v1`, `google-place:v1`, and typed
`club-provider:{seatengine_id,seatengine_v3_id,ticketmaster_id,eventbrite_venue_id}:v1`
use global ID scopes. `club-location:v1` uses exact normalized name plus an
address/city/state/country scope. Verified aliases retain the same location scope.
No fuzzy or name-only match grants approval. An approved hidden organizer proxy
is valid; visibility does not imply rejection or approval. Eventbrite organizer
source IDs are deliberately NOT venue identity keys.

Provider IDs, verified aliases and public IDs are retained when blocking or
deleting a club, including when reconciling imported blocks. Explicit country
conflicts prevent geographic matches. Compatibility place-ID denials also become durable decisions, including
when their legacy row is removed. A ledger restore does not erase a legacy
denial; resolve that evidence explicitly before subsequent approval.

Two same-name venues can have separate review identities. The existing public
`clubs.name` uniqueness constraint remains: publishing a second identity with the
same display name returns a conflict requiring location reconciliation, never an
automatic merge.

## Writers

- All five ClubHandler venue upserts (Eventbrite, SeatEngine/v3, Ticketmaster and
  discovered venues) record evidence and check authoritative policy before old
  matching paths, then verify the returned club identity.
- `bin/discover-nearby` records observations and reports pending venues as `review`
  and blocked venues as `denied`; neither is a `--new-only` onboarding suggestion.
  Repeated identical observations deduplicate. It cannot fall back on a failed
  policy lookup.
- Database triggers independently guard raw SQL imports, onboarding migrations,
  club inserts/updates, source upserts and show publication. Held INSERTs return
  no row; held UPDATEs preserve the previous row. Callers must inspect results.
- Admin create records an actor-attributed approval in the same transaction as
  club creation and its audit entry. Existing blocks and ambiguity prevent it.
- The shared curation service uses the club adapter for preview and approval.
  Approving an unbound candidate creates its public club without configuring any
  scraper. Approval of an existing club preserves its visibility.

## Effects and restoration

Blocking hides the public club and all its shows, and prevents republishing,
source reactivation and admission. Status (active/closed), scraper configuration,
enabled flags and comedy gates remain separate. Explicit hiding and source
disabling remain possible while held. Ingestion refreshes preserve existing
source enablement, even without special disposition metadata.

Restore is an audited blocked-to-pending decision. It does not republish shows,
unhide clubs, enable sources or broaden comedy gates. Reapproval and publication
are separate actions. Restored venues cannot silently regain admission.

## Rollout and verification

Reconcile legacy curation identities using CURATION-MIGRATION.md before enabling
these guards; existing pending clubs require explicit approval. Do not infer
approval from visibility, operating status or an enabled source. The migration
projects already-imported club blocks onto club/show visibility; it does not
mass-approve legacy venues. No production backfill or migration was run as part
of implementation.

The shared intake lock serializes policy changes and publication statements to
close check/write races. This favors correctness; throughput should be monitored
at rollout. PGlite tests exercise the real migration and shared service, but do
not benchmark multi-connection lock contention.

Run `cd apps/scraper && .venv/bin/python3 -m pytest tests/integration/test_curation_club_intake.py -q`.
The contract includes raw imports, scoped identities, retained aliases/provider
keys, compatibility denials, imported blocks, hidden proxies, explicit restore,
admin publication, ambiguity and unavailable policy. Python unit tests cover
all five ingestion entry points and discovery admission.
