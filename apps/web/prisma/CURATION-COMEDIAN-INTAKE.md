# Comedian admission boundary (TASK-4179)

`20261014190000_comedian_curation_intake` activates database enforcement. Apply the
TASK-4178 reconciliation runbook **before deploying this migration**: existing
visible/validated profiles are not automatically approved. Pending identities keep
existing public records/appearances but cannot acquire new trusted appearances or
enrichment. This change does not run a production backfill or clean up old records.

## Writer inventory

| Writer | Boundary and behavior |
| --- | --- |
| Scraper `ComedianHandler.stage_identity_candidates`, `ShowHandler.update_show_lineups` | Record raw observations before heuristics, stage unknown identities, resolve only approved policy. Failure aborts the batch; no legacy fallback. |
| Scraper `ComedianQueries.BATCH_ADD_COMEDIANS`, `insert_comedians` | Existing validation filter plus universal `comedians` INSERT guard. |
| `LineupQueries.BATCH_ADD_LINEUP_ITEMS`, title/alias matching | Policy-gated matching plus INSERT/UPDATE guard on `lineup_items`; stale in-memory matches cannot admit a blocked person. |
| Admin `/api/admin/comedians` POST | Authenticated explicit approval creates a ledger decision in the same transaction before Prisma creation. |
| Review Inbox `reviews.ts` approve/link/reject/undo | Approval ledger precedes publication; candidate rejection records a block; undo checks the recorded curation version and appends explicit restore. Selected appearances remain separate. |
| Admin PATCH, enrichment handlers/scripts, social/tour/website updates | Every `comedians` UPDATE passes the guard. Unapproved/blocked enrichment leaves the row unchanged. Visibility-only changes never remove curation decisions. |
| `scripts/core/reconcile_deny_list.py`, archived repair scripts, direct SQL/import/upsert | Same database triggers. Unapproved inserts create observation/candidate evidence and return no canonical row; callers must inspect RETURNING/row counts. |
| Show-collapse/repair scripts inserting or reassigning lineups | Same lineup INSERT/UPDATE guard; existing history is retained. |
| New orphan `comedian_deny_list` entries | Append a durable exact-name rule immediately. Removing the legacy row alone does not restore the rule. |

These are integrity guards, not database-role authorization. Application routes
continue to require admin authentication. Database owners can disable triggers;
maintenance code must not do so to bypass review.

## Identity and restore contract

`curation_comedian_policy` resolves exact normalized names, bound public IDs,
`comedian-uuid:v1` keys, migrated UUID/candidate keys, and caller-supplied scoped
provider keys. `curation_comedian_row_keys` maps Bandsintown/Songkick IDs using the
same provider namespace hash as `migration.providerKey`. The scraper's generic
comedian model has no provider extraction ID: do not substitute a show ID or URL
for a performer ID. Future providers must pass their real namespaced keys to
`curation_observe_comedian` before writing.

Confirmed alias edges propagate negative decisions. Unconfirmed legacy parent
links and multiple unresolved identity roots hold admission. Exact-name rules
preserve accents/punctuation and Unicode whitespace/NFC semantics; they never use
substring matching. No implicit identity merge occurs. Approval/link conflicts
require reconciliation, not automatic reassignment of owned keys.

The shared curation API registers the comedian adapter for block/restore. Approval
continues through performer identity review, which includes evidence, name and
appearance selection. Restore returns to pending; independent name rules, other
identity blocks and legacy hidden-name/deny-list suppression still apply. Neither
visibility toggles nor deleting a compatibility deny row erases ledger history.
Old review receipts without a curation version cannot use legacy undo to overwrite
new policy; use an explicit versioned curation restore instead.

## Concurrency and operation

Admission and policy mutations serialize on a real database lock-row update at the
statement boundary. This protects against concurrent new keys/blocks as well as
stale repeatable-read snapshots. Transactions must stay short and avoid network
calls after taking this lock. Serialization/deadlock errors roll back admission;
retry the entire transaction. This deliberately trades write concurrency for a
single authoritative decision; monitor ingestion latency before increasing worker
concurrency. The missing lock or policy schema is an error, never approval.

## Verification

- `npm test -- lib/admin/curation/comedianIntake.test.ts` executes actual migrations,
  direct SQL writes and real admin decisions against embedded PostgreSQL (PGlite).
- The required scraper command `python -m pytest tests/integration/test_curation_comedian_intake.py -q`
  invokes that same cross-language contract suite, without production credentials.
- Scraper handler/lineup suites check orchestration and SQL query behavior; legacy
  review unit tests isolate bridge functions, while the intake suite tests them
  against the real ledger and triggers.
- Multi-connection load/lock-contention benchmarking is not covered by PGlite.
