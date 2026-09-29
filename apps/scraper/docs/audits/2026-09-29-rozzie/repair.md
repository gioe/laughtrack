# Applied repair and rollback

Applied only 20260929170000_correct_rozzie_relocation with local Prisma 6.5.0.
The deploy wrapper compared local migrations with the production migration
ledger first and refused unrelated pending migrations. Prisma recorded success;
the follow-up SELECT proves club 10970 actually changed (not a zero-row UPDATE).

Only address, zip_code, latitude and longitude changed. All foreign-key counts
and row fingerprints match exactly: 144 shows, 144 tickets, 243 tagged shows,
119 scraper-run links, 1 source and 1,577 click rows. Empty reference sets stayed
empty. The 58 upcoming shows and source configuration are unchanged.
See applied.json and the earlier before.json snapshot.

The DO block locks the club and matching source, verifies the name, existing
business place ID, website and AnyRoad plugin ownership, and accepts only the
exact reviewed before-state or an already-correct no-op state. A missing club
is a no-op in other environments. No broad postal/address backfill is involved.

## Rollback

rollback.sql is manual incident recovery only: it intentionally restores the
known-stale Basile address, blank ZIP and former coordinates. It validates
identity/source ownership and accepts only the exact repaired state; later
address/coordinate edits are refused. Run in a transaction using the production
connection, inspect the row, and commit only if rollback is actually wanted.
Prisma migration history is not rewritten by this SQL.

Before deployment, a production transaction proved apply, idempotent replay,
exact full-row restoration, repeated rollback no-op, rejection of identity and
source drift, and rollback refusal after a later edit. Every test mutation was
rolled back. validation.json records those results. Public API and ingestion
verification are documented separately.
