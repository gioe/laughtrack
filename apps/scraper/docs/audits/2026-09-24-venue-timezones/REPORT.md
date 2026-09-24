# Aggregate venue timezone repair — TASK-4045

Snapshot: 2026-09-24 16:43:41 UTC. The refreshed population contained 340 visible venues without a timezone, including 301 venues with 468 upcoming shows. The original task's counts were stale.

## Evidence and repair

We reviewed live source pages for all 340 venues. Current-event IANA metadata verified 276 venues; alternate event pages verified five more. Unambiguous regional address evidence verified another 18. Identity checks used venue name, street, postal code, event URL, and the source/stored UTC instant. Ambiguous regions and mismatched identities were left unresolved.

The production repair filled 299 venue timezones, covering 287 venues with 446 upcoming shows. A separate connection confirmed 41 visible venues remain without a timezone, including 14 with 22 upcoming shows. Every unresolved venue and its evidence is recorded in sources.json; TASK-4075 tracks resolution.

Migration 20260924170000_restore_verified_venue_timezones changes only clubs.timezone. It requires matching ID, name, address, postal code, visibility, and a NULL timezone. It never replaces an existing timezone. SHA-256: e06f710cea8e460ef8bfd43cf606b5c873bdce38bfcef62f1ff96b5c24d124e0.

Local PostgreSQL validation exercised all 299 updates, idempotence, identity/visibility guards, preservation of other columns and show timestamps, and rollback. A production rollback trial updated 299 rows and an immediate rerun updated zero. The committed production transaction produced the same counts. The before/after show fingerprint remained 881c6d3019725490fbd14324b1e1412e372003a219dd6a292da84daeb2f0a9ac. See migration-validation.json, production-rollback.json, and production-apply.json.

The SQL was applied directly as this focused repair; Prisma migration bookkeeping was not changed and no unrelated pending migrations were deployed. A later normal migration deployment safely skips the already-filled rows.

## Prevention

Next Stop ingestion now retains structured locality, region, and country information and extracts validated IANA metadata only from the current event's Flight record. It rejects invalid, conflicting, or unrelated event timezone values. The aggregate venue refresh preserves existing timezone metadata.

Central nightly enrichment uses conservative country-aware regional evidence. It no longer guesses the majority timezone of split-zone states or uses name-only Places matches. Canada suffix CA cannot silently become California. Existing legacy timezone helpers remain available to their callers. Address parsing handles retained US country suffixes and rejects foreign addresses as US city/state evidence.

## Production refresh and display verification

After the database repair, the updated worktree ingestion code fetched live pages and executed the actual aggregate upsert against production for four representative venues. All returned the expected venue ID and retained the repaired IANA zone. A fresh database read confirmed each stored show instant was unchanged. This is a direct production execution of the updated code, not a claim that the hosted scraper deployment has already completed.

The actual web formatShowDate helper was executed with host TZ=UTC using those production records. All four resulting local wall times matched the source:

| Venue | Zone | Previous display | Correct display |
| --- | --- | --- | --- |
| Steinhardt Brewing Co. | America/New_York | March 13, 7:30 pm EST | March 13, 7:30 pm EST |
| Antlers Whiskey Lounge | America/Moncton | March 13, 7:00 pm EST | March 13, 8:00 pm AST |
| Riverside, Lechlade | Europe/London | November 14, 3:00 pm EST | November 14, 8:00 pm GMT |
| Here & Now Lounge | Australia/Melbourne | January 9, 3:30 am EST | January 9, 7:30 pm GMT+11 |

See production-refresh.json and rendering.json for source URLs, dates, payloads, persisted instants, and exact formatted strings. Focused regression coverage passes 90 tests; the complete scraper commit gate also passes.

## Timestamp assessment and follow-ups

All 330 parsed pages in the original source sweep had source UTC instants equal to stored UTC instants. There is no evidence supporting a blanket timestamp shift, and none was performed.

Two Alberta venues (11709 and 12330) have future source offsets that conflict with the current system timezone rules. Their stored instants still match their source. Local pytz 2026.1.post1 and Node timezone data 2024a also disagree with current system rules after the province's November 2026 change. TASK-4073 covers runtime timezone data updates and confirming the intended advertised local times before any timestamp correction. Official reference: https://www.alberta.ca/albertas-new-time-system-abt.

Twelve sampled upcoming events were marked EventCancelled by their source. TASK-4074 covers cancellation filtering and reconciliation; this timezone repair did not remove them. TASK-4075 covers the 41 unresolved venues. These are explicit remaining issues, not guessed repairs.
