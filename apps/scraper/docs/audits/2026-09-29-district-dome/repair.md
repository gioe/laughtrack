# Applied postal correction

Migration 20260929180000_correct_district_dome_postal updates only address and
zip_code on club 554. Retains all other club fields and source87/SeatEngine534.
The production deploy checks for unrelated pending migrations before using the
pinned Prisma 6.5.0 binary. Follow-up SELECTs, not the exit code alone, verify
the reviewed row changed. See applied.json for before/after reference counts.

The atomic DO block locks the club and source and checks name, website,
Google business ID, source ownership and exact postal preimage. Missing club
is a no-op for other environments; exact repaired postal state is idempotent.
Drift causes an exception instead of an overwrite.

## Rollback

rollback.sql is deliberate incident recovery only. It restores the former
85054 embedded address and blank structured ZIP, which contradict the reviewed
operator address. Run in a transaction, inspect before committing, and do not
rewrite the Prisma ledger. It refuses later postal corrections or source/
identity changes. Apply, replay, rollback, repeated rollback and drift rejection
were validated in a production transaction with every mutation rolled back;
validation.json records these checks.

No show, ticket, lineup, tag, purchase-click record or source is changed. The
Carry On description and event discrepancy are separately tracked by TASK-4117;
this migration neither validates nor reassigns that inventory.
