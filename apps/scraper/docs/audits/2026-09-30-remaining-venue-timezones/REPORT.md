# Remaining aggregate venue timezone evidence — TASK-4075

Refreshed 2026-09-30 UTC. The cohort is the 41 **top-level** unresolved
entries from TASK-4045 sources.json, not its 59 intermediate unresolved
source-parser results. This audit fetched 51 source URLs using the scraper's
HttpClient.fetch_html stack and retained raw event status separately from
extraction: canceled events are now correctly excluded by the extractor.

## Dispositions

Every original row appears exactly once in dispositions.json. At capture,
38 still had NULL timezone and three were populated: Ionia Theatre,
Parker-Binns Vineyard, and Spanish Peaks Campground. Those values agree with
current event-bound IANA metadata and are preserved. The original September24
future inventory counts are historical; before.json includes refreshed show
instants and cancellation flags.

Three NULL venues have sufficient independent current location evidence:

| ID | Venue | Timezone | Identity resolution |
| --- | --- | --- | --- |
| 22761 | Cork It Gainesville | America/New_York | Official venue at118 Main St SW in Gainesville matches the source venue and stored118 Main St. The descriptive Main Street Market suffix does not identify another city or venue. Current event-bound IANA agrees. Official30501 differs from source/stored30506; postal correction is separate. |
| 45259 | Pinfish Entertainment | America/New_York | Official venue confirms91214 Overseas Hwy, Tavernier, Florida Keys. Highway/Hwy is an abbreviation; this is outside Florida's western Central-time counties. Missing event content is not treated as cancellation. |
| 56972 | Spymaker Axe Throwing | America/Detroit | Official venue confirms1235 South Center Rd, Burton MI, matching stored S Center Rd. Genesee County is outside the four Upper Peninsula Central-time counties. |

The remaining35 NULL rows have explicit dispositions:18 historical-source-only,
15 canceled-source-only, and two active unresolved venues. These are not silently
closed as repaired. Revisit historical/canceled-only metadata when current,
independent venue evidence or a verified scheduled event becomes available.
Hudson's On Main's official social page exposes only an Olney title, not an
address; Formosa's old event URL redirects to a different canceled event.
TASK-4121 already owns those inaccessible/redirected inventory cases.
Canceled source pages and unrelated nearby-event IANA fields were never used
as proof of the current venue. No timezone was inferred from a numeric offset.

## Separate Las Vegas correction

Context750 identified club4552, outside the original cohort. Rio's official
show page confirms The Empire Strips Back at3700 W Flamingo Rd, Las Vegas
NV89103. The IANA northamerica source places this Pacific location in
America/Los_Angeles; West Wendover and northern-border Nevada exceptions do
not apply. America/Vancouver diverges in winter under current timezone rules.
The repair explicitly expects old America/Vancouver and changes only timezone.
Stored show instants are retained; this does not reconcile different provider
showtimes or classify the burlesque program's comedy eligibility.

Sources, capture times, hashes and assessments are in independent-evidence.json.
Key references:
- https://www.corkitgainesville.com/about
- https://www.pinfishentertainment.com/attractions
- https://spymakers.com/frequently-asked-questions/
- https://www.riolasvegas.com/shows/the-empire-strips-back
- https://raw.githubusercontent.com/eggert/tz/main/northamerica

## Safety and validation

Migration20260930020000_resolve_remaining_venue_timezones is one atomic DO
statement. All four targets require exact ID/name/address/postal/visibility
matches. NULL backfills require NULL; the Las Vegas correction requires its
explicit old timezone. Already-correct rows are no-ops; any other timezone or
identity drift aborts. No addresses, postal codes, dates or dependencies change.

validate_repair.py runs the exact SQL and always rolls back using a dedicated
connection. Local temporary tables use the captured production identities and
503 show instants. The production-shaped rollback trial covered599 shows,
599 tickets,246 lineup items,1214 tags and3344 ticket clicks, with identical
before/after fingerprints. The live scraper added inventory between the first
snapshot and this trial; the different totals are separate capture times.
Both trials pass idempotence and28 identity/current-timezone drift scenarios.
The production transaction never commits in this validator.

Run from repo root with the scraper Python:

    python apps/scraper/docs/audits/2026-09-30-remaining-venue-timezones/validate_repair.py --local-dsn 'host=127.0.0.1 port=55475 dbname=postgres user=postgres' --output /tmp/local-proof.json
    python apps/scraper/docs/audits/2026-09-30-remaining-venue-timezones/validate_repair.py --env-file apps/scraper/.env --output /tmp/rollback-proof.json

Production deployment counts and representative API/local-time checks will be
recorded in TASK-4075 durable context after the guarded migration deploys.
