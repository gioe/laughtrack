# Legacy curation backfill (TASK-4178)

This is an operator-run shadow backfill, not an automatic Prisma data migration. Deploying this code does not import decisions, clean up inventory, change legacy tables, enable adapters, or broaden event enforcement. TASK-4159 owns historical show cleanup and TASK-3982 owns blocked-lineup repair.

## Run a bounded dry run

Use an explicitly configured `DATABASE_URL`. The launcher never reads production credentials or chooses a database automatically. From `apps/web`:

```sh
bin/migrate-curation --source comedian_deny_list --environment laughtrack-prod --limit 10 > /tmp/curation-plan.json
```

The CLI starts a read-only repeatable-read transaction. Output contains source rows, referenced evidence/audit history, proposed entities/edges, notes, conflicts, reconciliation counts, a snapshot digest, destination fingerprint, and the next cursor. Review and retain the JSON securely: it contains original admin IDs, reasons and evidence. Database credentials are never printed. Keep the environment namespace fixed across every run; use a distinct namespace for independent databases.

Run every source category: `comedians`, `comedian_deny_list`, `clubs`, `venue_deny_list`, `podcast_deny_list`, `comedian_identity_candidates`, `comedian_podcasts`, `podcast_candidate_reviews`, `comedy_event_reviews`. The first two domain sources inventory flags, existing parent links and routing visibility, including records that will remain pending. Pagination uses deterministic text ordering with C collation (not numeric ordering). Pass the returned `nextCursor` as `--after` with the same source/environment. Primary batches default to 10 and cannot exceed 50 rows; individual dependency collections cap at 5,000 and plans at 10 MB. Oversized records fail closed instead of silently losing history.

## Mapping contract

| Legacy source                 | Durable mapping                                                                                                                                                                                                                                                                                      |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hidden comedian               | Block its typed entity and normalized exact-name rule, preserving current name-based suppression. Missing attribution is explicitly `legacy:unattributed`.                                                                                                                                           |
| Comedian deny name            | Block-only exact-name identity; retain it even when the public comedian no longer exists.                                                                                                                                                                                                            |
| Hidden club / organizer proxy | Identity plus visibility evidence only. Never infer an intake block from visibility.                                                                                                                                                                                                                 |
| Venue deny place ID           | Block the uniquely matched club, or a durable unmaterialized place identity. Multiple club matches are held.                                                                                                                                                                                         |
| Podcast denial                | Resolve public ID, exact provider key and exact feed URL. Different matching podcasts are held. Retain keys even for deleted public records.                                                                                                                                                         |
| Podcast restoration           | On first import, retain attributed block → restore history and finish pending. Later positive drift cannot automatically clear an existing negative decision.                                                                                                                                        |
| Identity candidate            | Keep rejected candidate identity blocked, with extraction evidence. Approve only when a non-undone admin approval audit matches the current candidate revision, actor, reviewed timestamp and canonical target, with no conflicting legacy suppression. Unproven/link-only acceptance stays pending. |
| Parent link                   | Typed child → parent proposal and original evidence. Existing links without proof are not invented human confirmations. Missing/self parents are held.                                                                                                                                               |
| Podcast association/candidate | Typed host/cohost proposal, or retained rejection. Confirm only a currently matching explicit admin approval. Mixed accepted/rejected source decisions and unknown roles are held rather than silently merged or widened. Unmaterialized candidates retain provider keys.                            |
| Event review                  | Preserve the original action, actor/reason, observation generation, payload/identity fingerprints and policy version as evidence. It does not become a permanent show or series block/approval. Existing scoped eligibility remains authoritative.                                                   |

All original row snapshots and referenced admin review/action histories are retained in append-only observations, including decisions that do not map safely to an active disposition. A matching positive audit is evidence of a specific review, not merely a non-null `reviewed_by` field. Current approvals with changed timestamps/revisions do not inherit old human attribution. Historical timestamps are preserved on imported ledger entries; missing timestamps are retained as missing in provenance rather than claimed as known.

`providerKey(source,id)` and `legacyKey(environment,table,id)` in `migration.ts` define reusable key contracts. Provider namespaces hash the exact source string; scope retains the original source and values are opaque. Feed URLs use `podcast-feed:exact:v1` without heuristic URL rewriting. Exact names use `normalizeExactNameV1`. No fuzzy names or titles establish identity. Existing key owners and typed public bindings must agree; conflicts require reviewed reconciliation, never silent key reassignment.

## Guarded apply and restart

After reviewing a saved page:

```sh
bin/migrate-curation --apply --plan /tmp/curation-plan.json --actor operator:your-id
```

Apply rejects a different database destination or changed legacy snapshot. It reconstructs the plan from live data rather than trusting edited JSON effects. A bounded transaction takes short maintenance locks on legacy dependency tables and curation tables, with a three-second lock timeout and a 60-second CLI transaction timeout. Use a quiet window and small pages; lock contention fails rather than waiting indefinitely. Legacy writers may pause briefly. No external side effects occur inside this transaction.

Each item has a savepoint. Conflicts roll back that entire item, report `held`, and allow independent rows to continue. Applied items have append-only observations keyed by source, row key and content fingerprint. Retrying an unchanged page returns `skipped` without repeating decisions or effects. A process interruption rolls back its transaction; use the same saved plan if its snapshot still matches. Newer non-migration decisions cannot be overwritten. Reports distinguish imported, skipped and held counts. Held rows remain on the reconciliation checklist even when advancing the cursor.

A page is not proof of whole-database convergence. Complete every category, then rescan from the beginning to catch rows inserted before prior cursors and legacy changes during the run. Review every held row and key collision. Repeat until the expected imported/skipped counts reconcile and the legacy change window is accounted for. Only subsequent adapter tasks may authorize cutover; do not enable them merely because one batch succeeded.

## Mixed-version compatibility and restoration

Legacy writers, deny lists, public visibility, parent links, associations and scoped event reviews remain untouched and authoritative throughout this task. Old services can roll back immediately without a reverse data migration. New adapters must combine legacy suppression with durable negative state; `migrationCompatibility` supplies a conservative reconciliation overlay for already materialized durable targets and never grants approval. It is an operator reconciliation helper, not an optimized ingestion hot path. Writer adapters still need their existing source-specific checks, locks, and both old/new suppression reads until cutover. Legacy changes require a fresh plan; positive changes do not silently erase durable negative decisions.

To reconcile a migrated block after an explicit legacy restoration, first use the existing legacy review workflow. Preview the durable target:

```sh
bin/migrate-curation --restore <durable-id> --target entity
```

The preview returns current version, effective suppression and remaining legacy reasons. After reviewing it:

```sh
bin/migrate-curation --restore <durable-id> --target entity --expected-version <version> --actor operator:your-id --reason 'Verified legacy restoration' --apply
```

Use `--target relationship` for an edge. Restoration requires the expected version, no remaining legacy suppression (including blocked endpoints for edges), and a latest decision owned by this migration. It appends an attributed restore decision and returns entity to pending or edge to proposed. It never publishes, approves, clears a separate name rule, or restores unrelated links. Newer manual decisions must use the authoritative review workflow. Do not delete keys, observations or history to roll back. If an import is wrong while legacy suppression remains active, hold it for review and correct the source explicitly; this helper cannot bypass that suppression.

Regression tests exercise dry-run isolation, all source categories, source-change rejection, idempotent replay, retained deletion-resistant identities, conflicting source decisions, historical restoration, explicit restoration guards, newer manual decisions, and unchanged legacy tables. These tests use isolated PostgreSQL-compatible fixtures; this task does not apply a production backfill or claim an audited production inventory.
